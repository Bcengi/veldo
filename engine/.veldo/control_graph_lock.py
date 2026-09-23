"""The exact LangGraph runtime lock for the graph adapter (VELDO-0043). Data, standard library only.

Every package in LangGraph's installed closure, pinned to one exact version and to the sha256 of
the one wheel resolved for PYTHON on PLATFORM. The pins are the latest stable releases PyPI served
on RESOLVED that satisfy the closure's own requirements; proof/VELDO-0043/README.md lists each
package's license, origin, owner approval and, where the pin is not the latest release, the
requirement that caps it.

The runtime built from this lock is content-addressed by digest(): a lock change finds no stale
runtime. VELDO-0045 later makes engine/runtime/ the canonical lock location and enforces the
hashes at activation; until then control_graph_install.py installs with pip --require-hashes.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd

SCHEMA = 'veldo.graph-runtime-lock/v1'
RESOLVED = '2026-09-23'
PYTHON = '3.12'
PLATFORM = 'linux x86_64, manylinux wheels, CPython 3.12 (cp312)'
ROOT_REQUIREMENT = 'langgraph==1.2.12'

# (name, version, wheel, sha256)
PACKAGES = (
    ('annotated-types', '0.8.0',
     'annotated_types-0.8.0-py3-none-any.whl',
     'f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0'),
    ('anyio', '4.15.1',
     'anyio-4.15.1-py3-none-any.whl',
     '6152fdbbf9a77fdec97731721bebf7c4c44f7c29b424b0065826173efc7ed101'),
    ('certifi', '2026.7.22',
     'certifi-2026.7.22-py3-none-any.whl',
     '62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775'),
    ('charset-normalizer', '3.5.1',
     'charset_normalizer-3.5.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl',
     'b9af956078716df40d985fb0dfeb2c2120c5ca92ba4ff4b388acfd01cdc14d08'),
    ('distro', '1.9.0',
     'distro-1.9.0-py3-none-any.whl',
     '7bffd925d65168f85027d8da9af6bddab658135b840670a223589bc0c8ef02b2'),
    ('h11', '0.16.0',
     'h11-0.16.0-py3-none-any.whl',
     '63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86'),
    ('httpcore', '1.0.9',
     'httpcore-1.0.9-py3-none-any.whl',
     '2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55'),
    ('httpcore2', '2.13.1',
     'httpcore2-2.13.1-py3-none-any.whl',
     'e1e05d4f25f7d7d496bfb96748f6f4b67657b03da069b3a68c36069f3db73d0a'),
    ('httpx', '0.28.1',
     'httpx-0.28.1-py3-none-any.whl',
     'd909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad'),
    ('httpx2', '2.13.1',
     'httpx2-2.13.1-py3-none-any.whl',
     '6dff50fabc270ee5fd25d845d0b078ed20564579744d6d962850975996d2f9a4'),
    ('idna', '3.20',
     'idna-3.20-py3-none-any.whl',
     'ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c'),
    ('jsonpatch', '1.33',
     'jsonpatch-1.33-py2.py3-none-any.whl',
     '0ae28c0cd062bbd8b8ecc26d7d164fbbea9652a1a3693f3b956c1eae5145dade'),
    ('jsonpointer', '3.1.1',
     'jsonpointer-3.1.1-py3-none-any.whl',
     '8ff8b95779d071ba472cf5bc913028df06031797532f08a7d5b602d8b2a488ca'),
    ('langchain-core', '1.6.4',
     'langchain_core-1.6.4-py3-none-any.whl',
     '2f940c83f787676ad4dc651d49d053c7ec34bda5a6afcd224da2863ff53a0b84'),
    ('langchain-protocol', '0.0.19',
     'langchain_protocol-0.0.19-py3-none-any.whl',
     '4cdf879a492a35980fd859ae792d3c65458ccaae504e183c9a10d7eac1f0720f'),
    ('langgraph', '1.2.12',
     'langgraph-1.2.12-py3-none-any.whl',
     '95403af7b510de8d79164742f71daaf866c69ca804a8cb72bef2cc1fa1ab9813'),
    ('langgraph-checkpoint', '4.2.0',
     'langgraph_checkpoint-4.2.0-py3-none-any.whl',
     '0547fd228935a0b758865de3a3d6d7a2537c308895d0f9ab092ce9151b5da942'),
    ('langgraph-prebuilt', '1.1.0',
     'langgraph_prebuilt-1.1.0-py3-none-any.whl',
     '51e311747d755b751d5c6b39b0c1446124d3a7643d2515017e6714b323508fc9'),
    ('langgraph-sdk', '0.4.5',
     'langgraph_sdk-0.4.5-py3-none-any.whl',
     'e03ef033a20d21288af496e9b6c08ae3afcc1b58dc5abcd37575bfd1a93045de'),
    ('langsmith', '0.14.0',
     'langsmith-0.14.0-py3-none-any.whl',
     '1a89e52c24edd6f4c24d8cfb32857814ceb5b9bec344a2850e86ab38475de362'),
    ('orjson', '3.12.0',
     'orjson-3.12.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
     '1192a7021b6d071aaf909864f6e924d6a2675ca360485b972b8401749311750b'),
    ('ormsgpack', '1.12.2',
     'ormsgpack-1.12.2-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
     '58d379d72b6c5e964851c77cfedfb386e474adee4fd39791c2c5d9efb53505cc'),
    ('packaging', '26.3',
     'packaging-26.3-py3-none-any.whl',
     'd7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c'),
    ('pydantic', '2.13.5',
     'pydantic-2.13.5-py3-none-any.whl',
     '346a034f080da3755d8e9cb5e00e8b07de1d39e4f6e2c87d8ab7cafa0b269a73'),
    ('pydantic_core', '2.46.5',
     'pydantic_core-2.46.5-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
     '0fc5be0abd4a407e200d844b404e33639a554e7bd0d448e7b9ae181be4789ac2'),
    ('PyYAML', '6.0.3',
     'pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl',
     'ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc'),
    ('requests', '2.34.2',
     'requests-2.34.2-py3-none-any.whl',
     '2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0'),
    ('requests-toolbelt', '1.0.0',
     'requests_toolbelt-1.0.0-py2.py3-none-any.whl',
     'cccfdd665f0a24fcf4726e690f65639d272bb0637b9b92dfd91a5568ccf6bd06'),
    ('sniffio', '1.3.1',
     'sniffio-1.3.1-py3-none-any.whl',
     '2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2'),
    ('tenacity', '9.1.4',
     'tenacity-9.1.4-py3-none-any.whl',
     '6095a360c919085f28c6527de529e76a06ad89b23659fa881ae0649b867a9d55'),
    ('truststore', '0.10.4',
     'truststore-0.10.4-py3-none-any.whl',
     'adaeaecf1cbb5f4de3b1959b42d41f6fab57b2b1666adb59e89cb0b53361d981'),
    ('typing-inspection', '0.4.4',
     'typing_inspection-0.4.4-py3-none-any.whl',
     '65b8397ba37ccbce054456aaccddfc91e6e3083c92824df348d96ca832f3f147'),
    ('typing_extensions', '4.16.0',
     'typing_extensions-4.16.0-py3-none-any.whl',
     '481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8'),
    ('urllib3', '2.8.0',
     'urllib3-2.8.0-py3-none-any.whl',
     '0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3'),
    ('uuid_utils', '0.17.1',
     'uuid_utils-0.17.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
     'd45f93f362d39f63ba14bbd9e4e1dd89fbed4de9bbef6bb428a379bd86571da2'),
    ('websockets', '16.1.1',
     'websockets-16.1.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl',
     '0f62863e8a00a6d33c3d6566ec0b89f23787b747ffe0c3bc71ec0e76b82c94b1'),
    ('xxhash', '4.0.1',
     'xxhash-4.0.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl',
     '237b8f63a2a0fcfb1ffc06e21dad23add44e6d354b2b014364a1d41e419a4dee'),
    ('zstandard', '0.25.0',
     'zstandard-0.25.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl',
     '5a56ba0db2d244117ed744dfa8f6f5b366e14148e00de44723413b2f3938a902'),
)


def data():
    return {'schema': SCHEMA, 'python': PYTHON, 'platform': PLATFORM, 'root': ROOT_REQUIREMENT,
            'packages': [list(row) for row in PACKAGES]}


def digest():
    """sha256 of the canonical lock data: the runtime's content address."""
    encoded = json.dumps(data(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def requirements():
    """pip requirements text: every package pinned exactly, with its one wheel hash."""
    return ''.join('%s==%s --hash=sha256:%s\n' % (name, version, sha256)
                   for name, version, _wheel, sha256 in PACKAGES)


def account_home():
    """The account's home from the password database, never $HOME (the gate replaces HOME)."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def runtime_directory(home=None):
    home = account_home() if home is None else Path(home)
    return home / '.local' / 'share' / 'veldo' / 'langgraph' / digest()
