import argparse
import datetime
import json
import pathlib
import sys
import time

import httpx
import trio

from holehe.core import check_update, import_submodules, get_functions, is_email, launch_module
from holehe.instruments import TrioProgress


def pickup_exists_and_rateLimit(out: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    pickup_items = {
        "exists": [],
        "rate_limit": []
    }
    
    for item in out:
        if item["exists"] == True:
            pickup_items["exists"].append(item)
        elif item["rateLimit"] == True:
            pickup_items["rate_limit"].append(item)
            
    return pickup_items


async def maincore():
    parser = argparse.ArgumentParser(description="Holehe CLI")
    parser.add_argument("email",
                        nargs='+', metavar='EMAIL',
                        help="Target Email")
    parser.add_argument("-o", "--output",
                        help="Output file path")
    parser.add_argument("-T","--timeout", type=int , default=10, required=False,dest="timeout",
                    help="Set max timeout value (default 10)")
    parser.add_argument("-NP","--no-password-recovery", default=False, required=False,action="store_true",dest="nopasswordrecovery",
                    help="Do not try password recovery on the websites")
    args = parser.parse_args()
    email = args.email[0]
    output = args.output
    
    check_update()
    
    if not is_email(email):
        print("Invalid email", file=sys.stderr)
        sys.exit(1)
    
    # import modules
    modules = import_submodules("holehe.modules")
    websites = get_functions(modules, args)
    
    # get timeout
    timeout = args.timeout
    
    # start time
    start_time = time.time()
    
    # define the async client
    client = httpx.AsyncClient(timeout=timeout)
    
    # launch the modules
    out = []
    # instrument = TrioProgress(len(websites))
    # trio.lowlevel.add_instrument(instrument)
    async with trio.open_nursery() as nursery:
        for website in websites:
            nursery.start_soon(launch_module, website, email, client, out)
    # trio.lowlevel.remove_instrument(instrument)
    
    # sort by modules names
    out = sorted(out, key=lambda x: x["name"])
    
    # close the client
    await client.aclose()
    
    # pickup exists and rateLimit
    pickup_items = pickup_exists_and_rateLimit(out)
    
    # print the results for json output
    if output:
        with open(output, "w") as f:
            json.dump(pickup_items, f, indent=4, ensure_ascii=False)
        print(f"{pathlib.Path(output).resolve()}")
    else:
        print(json.dumps(pickup_items, indent=4, ensure_ascii=False))


def main():
    trio.run(maincore)
    

if __name__ == "__main__":
    main()
    
