"""The string packages (strip/*.sp) the engine and game code look text up in.

The text is written for this project. Which references exist comes from the
GPL source: every reference the code asks for gets an entry, with the text
below or, without one, a readable version of its name. Strings used as
format strings keep exactly the format specifiers the code passes."""

import os
import re

from common import ROOT, write_text

# package file -> (ID, REFERENCE prefix the code uses)
PACKAGES = {
    # these two IDs are fixed: the engine looks text up in them by number
    # (src/strings/*.h), index 0 being the first reference in name order
    'str_server': (1, 'STR_SERVER'),
    'con_text': (3, 'CON_TEXT'),
    'mp_ingame': (2, 'INGAMETEXT'),
    'mp_svgame': (4, 'SVINGAME'),
    'sp_ingame': (5, 'INGAME'),
    'keynames': (6, 'KEYNAMES'),
    'menus0': (7, 'MENUS0'),
    'menus3': (8, 'MENUS3'),
}

TEXT = {
    'STR_SERVER': {
        'SERVER_NOT_RUNNING': 'The server is not running.',
    },
    'CON_TEXT': {
        'DUMP_USAGE': 'usage: condump <filename>',
        'NO_DEMO_SELECTED': 'No demo selected.',
    },
    'INGAMETEXT': {
        'KILLED_MESSAGE': 'You beat',
        'PLACE_WITH': 'place with',
        'TIED_FOR': 'Tied for',
        'KILLEDBY': 'Beaten by',
        'STARTS_IN': 'Starts in',
        'PICKUPLINE': 'Picked up',
        'SPECTATOR': 'Watching',
        'FOLLOWING': 'Following',
        'WAITING_FOR_PLAYERS': 'Waiting for players',
        'WAITING_TO_PLAY': 'Waiting to play',
        'SPEC_CHOOSEJOIN': 'Press Esc to join the game',
        'SPECHUD_VERSUS': 'vs',
        'DUELING': 'Dueling',
        'DUEL_WINS': 'Wins',
        'LEADER': 'Leader',
        'READY': 'Ready',
        'PLEASE_WAIT': 'Please wait...',
        'CONNECTION_INTERRUPTED': 'Connection interrupted',
        'SERVER_CHANGING_MAPS': 'The server is changing maps',
        'WAITING_FOR_NEW_KEY': 'Press a key, or Esc to cancel',
        'OF': 'of',
        'WITH': 'with',
        'PLACE': 'place',
        'NUMBER_ST': 'st', 'NUMBER_ND': 'nd', 'NUMBER_RD': 'rd', 'NUMBER_TH': 'th',
        'W_L': 'W/L',
        'FRAGLIMIT': 'Score limit:',
        'TIMELIMIT': 'Time limit:',
        'CAPTURELIMIT': 'Capture limit:',
        'WINLIMIT': 'Win limit:',
        'MAXFORCERANK': 'Power rank:',
        'SABERONLYSET': 'Blades only',
        'FORCEBASEDTEAMS': 'Teams by side',
        'CHEATSAREENABLED': 'Cheats are on',
        'PURE_SERVER': 'Pure server',
        'NOFPSET': 'No powers chosen',
        'SET_NEW_RANK': 'Your new rank applies when you respawn.',
        'GET_SABER': 'Pick up the blade!',
        'JMKILLED_NOTJM': 'Only the master scores.',
        'DIED_GENERIC': 'died',
        'MASTERY0': 'Rank 0', 'MASTERY1': 'Rank 1', 'MASTERY2': 'Rank 2', 'MASTERY3': 'Rank 3',
        'MASTERY4': 'Rank 4', 'MASTERY5': 'Rank 5', 'MASTERY6': 'Rank 6', 'MASTERY7': 'Rank 7',
        'RULES_FFA_1': 'Free for all: beat as many opponents as you can.',
        'RULES_DUEL_1': 'Duel: one on one, the winner stays.',
        'RULES_DUEL_2': 'Wait for your turn as a spectator.',
        'KILLED_SABER': 'was cut down by',
        'KILLED_MELEE': 'was knocked out by',
        'KILLED_FORCETOSS': 'was thrown by',
        'KILLED_DARKFORCE': 'was overpowered by',
        'KILLED_TELEFRAG': 'was squashed by',
        'KILLED_GENERIC': 'was beaten by',
        'KILLED_BLASTER': 'was shot by', 'KILLED_BOWCASTER': 'was shot by', 'KILLED_BRYAR': 'was shot by',
        'KILLED_REPEATER': 'was shot by', 'KILLED_REPEATERALT': 'was blasted by', 'KILLED_DISRUPTOR': 'was shot by',
        'KILLED_DISRUPTORSNIPE': 'was sniped by', 'KILLED_FLECHETTE': 'was shot by', 'KILLED_FLECHETTE_MINE': 'was caught by',
        'KILLED_ROCKET': 'was blasted by', 'KILLED_ROCKET_HOMING': 'was blasted by', 'KILLED_DETPACK': 'was blown up by',
        'KILLED_THERMAL': 'was blown up by', 'KILLED_TRIPMINE': 'was caught by', 'KILLED_TRIPMINE_TIMED': 'was caught by',
        'KILLED_SENTRY': 'was shot by', 'KILLED_STUN': 'was stunned by',
        'SUICIDE_SHOT_MALE': 'shot himself', 'SUICIDE_SHOT_FEMALE': 'shot herself', 'SUICIDE_SHOT_GENDERLESS': 'shot itself',
        'SUICIDE_EXPLOSIVES_MALE': 'blew himself up', 'SUICIDE_EXPLOSIVES_FEMALE': 'blew herself up',
        'SUICIDE_EXPLOSIVES_GENDERLESS': 'blew itself up',
        'SUICIDE_ELECTROCUTED_MALE': 'was shocked', 'SUICIDE_ELECTROCUTED_FEMALE': 'was shocked',
        'SUICIDE_ELECTROCUTED_GENDERLESS': 'was shocked',
        'GETTINGINFOFORSERVERS': 'Getting server info...', 'OR_PRESS_ESC_THEN_CLICK_VOTE': 'or press Esc and choose Vote',
        'SERVER_REFRESHTIME': 'Refresh time', 'SEEKER_ALREADYDEPLOYED': 'Already deployed.',
        'SENTRY_ALREADYPLACED': 'Already placed.', 'SENTRY_NOROOM': 'No room here.', 'SHIELD_NOROOM': 'No room here.',
        'RULES_TEAM_1': 'Teams: beat the other team.', 'RULES_TEAM_2': 'Points go to your team.',
        'RULES_CTF_1': 'Capture the flag: bring their flag to your base.', 'RULES_CTF_2': 'Your flag must be at home.',
        'RULES_CTY_1': 'Capture the item: bring it to your base.', 'RULES_CTY_2': 'Keep it away from the other team.',
        'RULES_HOLO_1': 'Collect the relics for power.', 'RULES_HOLO_2': 'Each relic gives a power.',
        'RULES_JEDI_1': 'Master duel: hold the master blade to score.', 'RULES_JEDI_2': 'Only the master scores.',
        'SUICIDE_FALLDEATH_MALE': 'fell too far',
        'SUICIDE_FALLDEATH_FEMALE': 'fell too far',
        'SUICIDE_FALLDEATH_GENDERLESS': 'fell too far',
        'SUICIDE_GENERICDEATH_MALE': 'gave up',
        'SUICIDE_GENERICDEATH_FEMALE': 'gave up',
        'SUICIDE_GENERICDEATH_GENDERLESS': 'gave up',
    },
    'INGAME': {
        'item_medpak_instant': 'Health +25',
        'item_shield_sm_instant': 'Shield +25',
        'item_shield_lrg_instant': 'Shield +100',
    },
    'SVINGAME': {
        'PLCONNECT': 'is connecting',
        'PLENTER': 'entered the game',
        'DISCONNECTED': 'left',
        'JOINEDTHEBATTLE': 'joined the fight',
        'JOINEDTHESPECTATORS': 'is watching',
        'JOINEDTHEREDTEAM': 'joined the red team',
        'JOINEDTHEBLUETEAM': 'joined the blue team',
        'PLRENAME': 'is now called',
        'WAS_KICKED': 'was kicked',
        'HIT_THE_KILL_LIMIT': 'hit the score limit',
        'TIMELIMIT_HIT': 'Time is up.',
        'PLDUELCHALLENGE': 'challenged you to a duel',
        'PLDUELCHALLENGED': 'You challenged',
        'PLDUELACCEPT': 'accepted the duel with',
        'PLDUELWINNER': 'won the duel against',
        'PLDUELTIE': 'tied the duel with',
        'PLDUELSTOP': 'stopped the duel with',
        'BEGIN_DUEL': 'Begin!',
        'VERSUS': 'vs',
        'CANTDUEL_BUSY': 'is busy.',
        'CANTDUEL_JUSTDID': 'You just challenged them.',
        'NODUEL_GAMETYPE': 'No duels in this game type.',
        'SERVER_DISCONNECTED': 'The server closed the connection.',
        'SERVER_CONNECTION_TIMED_OUT': 'The connection to the server timed out.',
        'SERVER_IS_FULL': 'The server is full.',
        'INVALID_PASSWORD': 'Wrong password.',
        'VOTEPASSED': 'The vote passed.',
        'VOTEFAILED': 'The vote failed.',
        'PLCALLEDVOTE': 'called a vote',
        'PLVOTECAST': 'Vote cast.',
        'NOVOTE': 'Voting is off on this server.',
        'NOCHEATS': 'Cheats are off on this server.',
        'MUSTBEALIVE': 'You must be alive.',
        'NOSWITCH': 'You can\'t switch now.',
        'ATTEMPTDUELKILL': 'tried to interrupt a duel', 'BECOMEJM': 'is the master now',
        'CANNOT_KICK_HOST': 'The host can\'t be kicked', 'FORCEAPPLIED': 'Your powers are set',
        'FORCEPOWERCHANGED': 'Your powers change when you respawn', 'MAXTEAMVOTES': 'No more team votes',
        'MAXVOTES': 'No more votes', 'MUSTBEDARK': 'This team takes the other side',
        'MUSTBELIGHT': 'This team takes the other side', 'NEWTEAMLEADER': 'is the new team leader',
        'NOSPECVOTE': 'Spectators can\'t vote', 'NOTEAMVOTEINPROG': 'No team vote in progress',
        'NOVOTEASSPEC': 'Spectators can\'t vote', 'NOVOTEINPROG': 'No vote in progress',
        'NOVOTE_MAPNOTSUPPORTEDBYGAME': 'That map doesn\'t support this game type',
        'ONLY_ADD_BOTS_AS_SERVER': 'Only the server can add bots', 'PLTEAMVOTECAST': 'Team vote cast.',
        'PRINTBLUETEAM': 'joined the blue team', 'PRINTFREETEAM': 'joined the fight', 'PRINTREDTEAM': 'joined the red team',
        'PRINTSPECTEAM': 'is watching', 'TEAMVOTEALREADY': 'A team vote is already in progress',
        'TEAMVOTEALREADYCAST': 'You already voted', 'TEAMVOTEFAILED': 'The team vote failed.',
        'TEAMVOTEPASSED': 'The team vote passed.', 'TOOMANYBLUE': 'The blue team is full',
        'TOOMANYBLUE_SWITCH': 'The blue team is full', 'TOOMANYRED': 'The red team is full',
        'TOOMANYRED_SWITCH': 'The red team is full', 'UNABLE_TO_ADD_BOT': 'Unable to add a bot',
        'VOTEALREADY': 'You already voted', 'VOTEINPROGRESS': 'A vote is already in progress',
    },
    'MENUS0': {'YES': 'Yes', 'NO': 'No', 'PING': 'Ping'},
    'MENUS3': {
        'LOADING_MAPNAME': 'Loading %s',
        'CONNECTING_TO': 'Connecting to %s',
        'STARTING_UP': 'Starting up...',
        'AWAITING_CHALLENGE': 'Waiting for the server...',
        'AWAITING_CONNECTION': 'Waiting for the server...',
        'AWAITING_GAMESTATE': 'Waiting for the game...',
        'AWAITING_SNAPSHOT': 'Waiting for the game...',
        'SERVERS_FOUNDWITH': '%d server%s with %s',
        'KEYBIND_OR': 'or',
        'NAME': 'Name', 'SCORE': 'Score', 'TIME': 'Time', 'GAME': 'Game', 'SOURCE': 'Source',
        'HUMAN': 'Human', 'CLOSED': 'Closed',
        'FORCEDESC_LIGHT': 'Calm', 'FORCEDESC_DARK': 'Fury',
    },
}

SOURCE_DIRS = ['src/mvsdk/code', 'src/client', 'src/server', 'src/qcommon']


def code_references():
    """{prefix: set(names)} of every reference the code asks for."""
    refs = {}
    pats = [
        re.compile(r'GetStripEdString\(\s*"([A-Z0-9_]+)"\s*,\s*"([A-Za-z0-9_]+)"'),
        re.compile(r'SP_GetStringTextString\(\s*"([A-Z0-9]+(?:_TEXT)?)_([A-Z0-9_]+)"'),
    ]
    simple = re.compile(r'"(KILLED_[A-Z_]+|SUICIDE_[A-Z_]+|MASTERY\d)"')
    at = re.compile(r'"@@@([A-Z0-9_]+)')
    for d in SOURCE_DIRS:
        for dirpath, _, files in os.walk(os.path.join(ROOT, d)):
            for name in files:
                if not name.endswith(('.c', '.cpp', '.h')):
                    continue
                text = open(os.path.join(dirpath, name), encoding='latin-1').read()
                for pat in pats:
                    for prefix, ref in pat.findall(text):
                        refs.setdefault(prefix, set()).add(ref)
                for ref in simple.findall(text):
                    refs.setdefault('INGAMETEXT', set()).add(ref)
                for ref in at.findall(text):
                    refs.setdefault('SVINGAME', set()).add(ref)
    return refs


def humanize(ref):
    return ref.replace('_', ' ').capitalize()


def package(file_id, prefix, entries):
    out = ['VERSION 1', 'ID %d' % file_id, 'REFERENCE %s' % prefix, 'COUNT %d' % len(entries)]
    for i, (ref, text) in enumerate(entries):
        text = text.replace('"', "'")
        out += ['INDEX %d' % i, '{', '   REFERENCE %s' % ref, '   TEXT_LANGUAGE1 "%s"' % text, '}']
    return '\n'.join(out) + '\n'


def generate(staging):
    refs = code_references()
    for fname, (file_id, prefix) in PACKAGES.items():
        names = set(TEXT.get(prefix, {})) | refs.get(prefix, set())
        entries = [(n, TEXT.get(prefix, {}).get(n) or humanize(n)) for n in sorted(names)]
        write_text(staging, 'strip/%s.sp' % fname, package(file_id, prefix, entries))
