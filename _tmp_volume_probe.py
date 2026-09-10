import libraries.utils.wwise.waapi_utils  # noqa: F401  解开循环导入
from libraries.waapi_client import WAAPIClient
from libraries.wwise_object import WwiseObject, WwiseObjectType

client = WAAPIClient().connect()
sound = WwiseObject.from_id(WAAPIClient().find_all_objects_by_type("Sound")[0]["id"])
print("probe object:", sound.path, flush=True)


def try_call(label, args):
    try:
        result = client.call("ak.wwise.core.object.get", args)
        first = (result or {}).get("return", [{}])[0]
        print(f"[{label}] keys={sorted(first.keys())}", flush=True)
    except Exception as e:
        print(f"[{label}] ERROR {e}", flush=True)


sid = sound.id
try_call("legacy+plain", {
    "from": {"id": [sid]},
    "options": {"return": ["id", "name", "Volume"]},
})
try_call("legacy+@", {
    "from": {"id": [sid]},
    "options": {"return": ["id", "name", "@Volume"]},
})
try_call("waql+plain", {
    "waql": f'from object "{sid}"',
    "options": {"return": ["id", "name", "Volume"]},
})
try_call("waql+@", {
    "waql": f'from object "{sid}"',
    "options": {"return": ["id", "name", "@Volume"]},
})
try_call("legacy two ids +@", {
    "from": {"id": [sid, sid]},
    "options": {"return": ["id", "name", "@Volume"]},
})
