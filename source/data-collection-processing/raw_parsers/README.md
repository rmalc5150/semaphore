# Shared raw-format parsers

`raw_parsers` is the single source of truth for raw-format code used by both
capture and metadata. Import it directly in new code. The old imports under
`metadata_engine` remain available for compatibility.

| Provider or format | Module |
| --- | --- |
| Canada NOC JSON and record identity | `raw_parsers.canada_noc` |
| ChiCTR HTML tables | `raw_parsers.chictr_tables` |
| Europe PMC JATS XML | `raw_parsers.epmc_fulltext` |
| NMPA HTML detail | `raw_parsers.nmpa_tables` |
| PMDA designation PDFs | `raw_parsers.pmda_tables` |
| PubMed XML | `raw_parsers.pubmed_enrichment` |

The package accepts provider bytes or text and has no dependency on the
metadata engine. AWS access, evidence loading, queue state, and publication
stay in the calling application. NMPA HTML parsing uses `lxml`, and PMDA PDF
parsing uses `pdfplumber`. Both use the consumer's existing dependency set.

## Updating and deploying

1. Update the parser here and add or update its fixture. If an output field or
   validation rule changes, check its effect on collection identities and
   evidence validation before replaying existing observations.
2. Bump `__version__` in `__init__.py` for every published code change. Add new
   parser modules to `MODULES` so the worker bundles include them.
3. Run the parser and application tests, then build and verify the release.

```bash
python -m raw_parsers.release /tmp/raw-parser-release
cd /tmp/raw-parser-release
sha256sum --check raw-parsers-1.0.0.sha256
```

Collection and metadata build scripts include the same source package. For an
isolated consumer, pin the verified ZIP itself on Python's import path, or unzip
it into the application root next to the consumer:

```bash
PYTHONPATH=/opt/optima/raw-parsers-1.0.0.zip python -c 'from raw_parsers import __version__; print(__version__)'
```

Deploy a pinned release to each consumer. Do not import mutable code from a
remote URL or edit a worker's copy independently. Keep the previous release
available so it can be selected again if a rollout fails. Publishing a new parser
release does not reset existing capture or metadata state.

On the two existing capture instances, the worker virtual environments read
`/opt/constellation/raw-parser-releases/current`. To switch to a release there,
copy the verified ZIP and `install_raw_parser_release.py` to the worker and run:

```bash
sudo python3 install_raw_parser_release.py raw-parsers-1.0.0.zip \
  --sha256 SHA256_FROM_THE_RELEASE_CHECKSUM \
  --releases /opt/constellation/raw-parser-releases
```

New jobs see the selected release without a service restart. To roll back, run
the same command with the previous ZIP and its checksum.
