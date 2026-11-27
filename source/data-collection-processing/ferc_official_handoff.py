"""Stream nested FERC provider filing CSVs into bounded native Parquet shards."""
from collections import Counter
import codecs
import csv
import hashlib
import io
import json
import re
from zipfile import ZipFile

import pyarrow as pa
import pyarrow.csv as arrow_csv
import pyarrow.compute as pc
import pyarrow.parquet as pq

from temporary_archive_formats import safe_members
from temporary_archive_intake import exact_bytes, put_checked
from temporary_archive_stage import CONTROL

NAME='FERC-Official-Q1-2016-Filings.zip'
KINDS={'contracts','transactions','ident','indexpub'}
RELEASE='ferc_official_2016q1'
CHUNK_ROWS=1_000_000


def decode_legacy_bytes(error):
    raw=error.object[error.start:error.end]
    # Windows exports may include a legacy byte within otherwise UTF-8 text.
    text=''.join(bytes([value]).decode('cp1252',errors='surrogateescape') for value in raw)
    text=''.join(chr(ord(value)-0xDC00) if 0xDC80<=ord(value)<=0xDCFF else value for value in text)
    return text,error.end


codecs.register_error('ferc_legacy_byte',decode_legacy_bytes)


def text_column(column,transcoded,kind):
    try:
        return pc.cast(column,pa.string())
    except pa.ArrowInvalid:
        values=[]
        for raw in column.to_pylist():
            if raw is None:
                values.append(None)
                continue
            try:
                value=raw.decode('utf-8')
            except UnicodeDecodeError:
                transcoded[kind]+=1
                value=raw.decode('utf-8',errors='ferc_legacy_byte')
            values.append(value)
        return pa.array(values,type=pa.string())


class Shards:
    def __init__(self,s3,root,workspace,kind,columns):
        self.s3,self.root,self.workspace,self.kind=s3,root,workspace,kind
        self.columns=columns
        self.schema=pa.schema([(n,pa.string()) for n in columns]+[
            ('filing_package',pa.string()),('filing_member',pa.string()),('native_row',pa.int64())])
        self.items=[]
        self.pending=0
        self.total=0
        self.writer=None
        self.path=workspace/(kind+'.parquet')

    def write(self,table):
        while table.num_rows:
            if self.writer is None:
                self.writer=pq.ParquetWriter(self.path,self.schema,compression='zstd')
            take=min(CHUNK_ROWS-self.pending,table.num_rows)
            self.writer.write_table(table.slice(0,take))
            self.pending+=take
            self.total+=take
            table=table.slice(take)
            if self.pending==CHUNK_ROWS:
                self.flush()

    def flush(self):
        if self.writer is None:
            return
        self.writer.close()
        self.writer=None
        if pq.ParquetFile(self.path).metadata.num_rows != self.pending:
            raise ValueError('native_ferc_shard_count_mismatch')
        chunk=f'{len(self.items):05}'
        with self.path.open('rb') as file:
            digest=hashlib.file_digest(file,'sha256').hexdigest()
            file.seek(0)
            artifact=put_checked(self.s3,f'{self.root}/tables/{self.kind}/{chunk}/{digest}/data.parquet',
                                 file,digest,self.path.stat().st_size,'application/vnd.apache.parquet')
        self.items.append({'dataset':'official_'+self.kind,'partition_id':chunk,'rows':self.pending,
                           'schema':[[field.name,str(field.type)] for field in self.schema],
                           'object':artifact})
        self.path.unlink()
        self.pending=0


def columns_for(stream):
    line=stream.readline(65537)
    if not line or len(line)>65536:
        raise ValueError('native_ferc_header_missing_or_oversized')
    fields=tuple(value.strip().lower() for value in next(csv.reader([line.decode('utf-8-sig')])))
    if len(set(fields))!=len(fields) or any(not re.fullmatch(r'[a-z][a-z0-9_]*',value) for value in fields):
        raise ValueError('native_ferc_header_is_not_supported')
    return fields


def prepare(s3, zip_path, raw, prefix, workspace):
    parent=raw['attachment']['sha256']
    key=f'{CONTROL}/handoff-provenance/{parent}/ferc.json'
    provenance=json.loads(exact_bytes(s3,key))
    if (provenance['archive']['sha256']!=raw['sha256']
            or provenance['archive']['bytes']!=raw['bytes']):
        raise ValueError('ferc_archive_not_identical_to_verified_provider_download')
    manifests={entry['filing_zip']:entry['members'] for entry in provenance['required_members']}
    originals={entry['name']:entry['bytes'] for entry in provenance['archive']['zip_members']}
    shards={}
    files=Counter()
    empty=Counter()
    rejected=Counter()
    transcoded=Counter()
    with ZipFile(zip_path) as archive:
        valid=set(safe_members(archive))
        if valid!=set(manifests) or {item.filename:item.file_size for item in archive.infolist()}!=originals:
            raise ValueError('ferc_filing_inventory_mismatch')
        for index,outer in enumerate(archive.infolist(),1):
            package=outer.filename
            if not re.fullmatch(r'CSV_2016_Q1_\d+_\d+\.ZIP',package,re.I):
                raise ValueError('unexpected_ferc_filing_package_id')
            with ZipFile(io.BytesIO(archive.read(outer))) as filing:
                native={item.filename for item in filing.infolist() if not item.is_dir()}
                if native!=set(manifests[package]) or len(native)!=len(filing.infolist()):
                    raise ValueError('ferc_filing_member_inventory_mismatch')
                for member in filing.infolist():
                    name=member.filename
                    match=re.fullmatch(r'[^/\\]+_(contracts|transactions|ident|indexpub)\.csv',name,re.I)
                    if not match:
                        raise ValueError('unexpected_ferc_filing_member')
                    kind=match[1].lower()
                    files[kind]+=1
                    with filing.open(member) as stream:
                        columns=columns_for(stream)
                        shard=shards.setdefault(kind,Shards(s3,prefix,workspace,kind,columns))
                        if shard.columns!=columns:
                            raise ValueError('ferc_native_header_changed')
                        if not stream.peek(1):
                            empty[kind]+=1
                            continue
                        position=0
                        def invalid(_):
                            rejected[kind]+=1
                            return 'skip'
                        reader=arrow_csv.open_csv(stream,
                            read_options=arrow_csv.ReadOptions(column_names=columns,block_size=2*1024**2),
                            parse_options=arrow_csv.ParseOptions(newlines_in_values=True,invalid_row_handler=invalid),
                            convert_options=arrow_csv.ConvertOptions(column_types={c:pa.binary() for c in columns},
                                 strings_can_be_null=False))
                        for batch in reader:
                            n=batch.num_rows
                            if not n:
                                continue
                            fields=[text_column(column,transcoded,kind) for column in batch.columns]
                            table=pa.Table.from_arrays(fields+[pa.repeat(package,n),pa.repeat(name,n),
                                     pa.array(range(position+1,position+n+1),type=pa.int64())],schema=shard.schema)
                            shard.write(table)
                            position+=n
                        if not position:
                            empty[kind]+=1
            if index%250==0:
                print(json.dumps({'native_ferc_filing_packages':index,
                                  'rows':sum(obj.total for obj in shards.values())}),flush=True)
    expected={n.lower():v for n,v in provenance['expected_counts'].items()}
    if files!=expected or set(shards)!=KINDS:
        raise ValueError('native_ferc_archive_table_member_counts_do_not_reconcile')
    for shard in shards.values():
        shard.flush()
    published=[table for kind in sorted(shards) for table in shards[kind].items]
    return {
        'representation':'Official FERC filing CSVs, with original filing packages distinguished from PUDL',
        'native_release':RELEASE, 'filing_packages':len(manifests), 'member_counts':dict(files),
        'empty_members':dict(empty), 'rejected_rows':dict(rejected),
        'legacy_encoding_values_transcoded':dict(transcoded),
        'rows':sum(shard.total for shard in shards.values()),
        'tables':{'official_'+kind:shard.total for kind,shard in shards.items()},
        'source_inventory':key,
    },published
