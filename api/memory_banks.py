"""Owner-local, bot-specific memory bank identities and migration visibility."""
from contextlib import closing
import hashlib
import re
import sqlite3
from pathlib import Path

BOT_BANK = re.compile(r'bot-([a-z0-9][a-z0-9_-]{0,63})--(private|[0-9a-f]{64})')


def bot_name(value):
    value = str(value or 'default')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', value):
        raise ValueError('Invalid memory bot')
    return value


def key(bot, conversation='private'):
    if conversation != 'private' and not re.fullmatch(r'[0-9a-f]{64}', conversation):
        raise ValueError('Invalid memory conversation')
    return f'bot-{bot_name(bot)}--{conversation}'


def valid_key(bank):
    return isinstance(bank, str) and (bank == 'private' or
        re.fullmatch(r'[0-9a-f]{64}', bank) or BOT_BANK.fullmatch(bank))


def describe(bank):
    match = BOT_BANK.fullmatch(bank)
    if not match:
        return dict(bot='', conversation=bank, label='Personal memories' if bank == 'private' else 'Conversation memories '+bank[:8])
    bot, conversation = match.groups()
    return dict(bot=bot, conversation=conversation,
                label='Bot '+bot+' · '+('private' if conversation == 'private' else 'conversation '+conversation[:8]))


def archived(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='bot_bank_migration'").fetchone()
                and db.execute("SELECT 1 FROM bot_bank_migration WHERE complete=1").fetchone())


def active_paths(directory=None):
    from api.config import STATE_DIR
    from api.personal_context import _safe
    candidates = (Path(directory).glob('*.db') if directory is not None else
                  (Path(STATE_DIR)/'personal_context').glob('*/mnemosyne/*.db'))
    paths = []
    for path in sorted(candidates):
        if not valid_key(path.stem):
            continue
        _safe(path)
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
            if not archived(db):
                paths.append(path)
    return paths


def source_reference(path, mid, metadata):
    """Company provenance survives the split without re-publishing old claims."""
    from api.config import STATE_DIR
    origin = metadata.get('company_source_id')
    if isinstance(origin, str) and re.fullmatch(r'[0-9a-f]{64}', origin):
        return origin
    return hashlib.sha256((str(path.relative_to(STATE_DIR))+':'+mid).encode()).hexdigest()
