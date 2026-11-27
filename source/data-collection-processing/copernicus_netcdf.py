"""Validate CDS container structure and scope without extracting measurements."""
from datetime import datetime,timedelta
from io import BytesIO
from pathlib import PurePosixPath
import stat
import zipfile

from regulatory_collection import SourceIssue,require

ALIASES={'2m_temperature':('t2m','2m_temperature'),
         'total_precipitation':('tp','total_precipitation')}


def members(body):
    if not body.startswith(b'PK\x03\x04'):
        yield body
        return
    with zipfile.ZipFile(BytesIO(body)) as archive:
        files=[i for i in archive.infolist() if not i.is_dir()]
        require(0<len(files)<=8 and sum(i.file_size for i in files)<=48*1024**2,
                'copernicus_netcdf_package_limit')
        seen=set()
        for item in files:
            path=PurePosixPath(item.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                    and path not in seen and not stat.S_ISLNK(item.external_attr>>16)
                    and not item.flag_bits&1,'copernicus_netcdf_unsafe_member')
            seen.add(path)
            yield archive.read(item)


def verify(body,start,end,request):
    from netCDF4 import Dataset,num2date

    first,last=datetime.fromisoformat(start),datetime.fromisoformat(end)
    keys=set(request['variable']); observed={name:set() for name in keys}
    require(keys and keys<=ALIASES.keys() and last>first,'copernicus_validation_request_scope')
    stamps=set()
    day=first
    while day<last:
        for t in request['time']:
            hours,minutes=map(int,t.split(':'))
            stamps.add((day+timedelta(hours=hours,minutes=minutes)).strftime('%Y-%m-%dT%H:%M:%S'))
        day+=timedelta(days=1)
    try:
        for file in members(body):
            require(file.startswith((b'CDF',b'\x89HDF')),'copernicus_netcdf_member_signature')
            with Dataset('cds-verified.nc',mode='r',memory=file) as ds:
                coordinate=next((ds.variables[n] for n in ('valid_time','time') if n in ds.variables),None)
                require(coordinate is not None and len(coordinate.shape)==1 and 0<coordinate.size<=len(stamps),
                        'copernicus_netcdf_time_dimension')
                dates=num2date(coordinate[:],coordinate.units,getattr(coordinate,'calendar','standard'))
                values={d.strftime('%Y-%m-%dT%H:%M:%S') for d in dates}
                require(len(values)==coordinate.size and values<=stamps,'copernicus_netcdf_time_mismatch')
                matched=False
                for name in keys:
                    var=next((ds.variables[n] for n in ALIASES[name] if n in ds.variables),None)
                    if var is None:continue
                    require(coordinate.dimensions[0] in var.dimensions and not observed[name]&values,
                            'copernicus_netcdf_duplicate_or_unscoped_variable')
                    observed[name].update(values);matched=True
                require(matched,'copernicus_netcdf_no_requested_variables')
    except (OSError,TypeError,AttributeError,ValueError,RuntimeError,zipfile.BadZipFile) as error:
        if isinstance(error,SourceIssue):raise
        raise SourceIssue('copernicus_netcdf_unreadable') from None
    require(all(values==stamps for values in observed.values()),'copernicus_netcdf_incomplete_time_or_variables')
    return {'variables':sorted(keys),'time_steps_per_variable':len(stamps),'start':min(stamps),
            'last_time':max(stamps),'measurements_extracted':False}
