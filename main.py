import httpx
import argparse
import hashlib
import time
from difflib import unified_diff

from bs4 import BeautifulSoup


def get_hash(s):
    return hashlib.sha256(s.encode()).hexdigest()


def get_content(site, selector):
    resp = httpx.get(site)
    out = resp.text

    if selector is not None:
        soup = BeautifulSoup(out, 'html.parser')
        targets = soup.select(selector)

        out = "\n".join([str(t) for t in targets])

    checksum = get_hash(out)
    content = (out, checksum)

    return content


def main(diff, site=None, selector=None, frequency=None, ntfy_channel=None, webhook_url=None):
    content = None
    succesive_errors = 0

    while True:
        next_content = None
        try:
            next_content = get_content(site, selector)
        except Exception as e:
            payload = f"Siteeagle for '{site}' had an error."
            if succesive_errors >= 3:
                payload = f"[TERMINATING!] {payload}"

            if webhook_url:
                httpx.post(webhook_url, data=payload)
            elif ntfy_channel:
                httpx.post(f"https://ntfy.sh/{ntfy_channel}", data=payload)

            if succesive_errors >= 3:
                raise e

            succesive_errors += 1
            time.sleep(frequency)
            continue

        if content is not None:
            if content[1] != next_content[1]:
                if diff:
                  payload = "".join(l for l in unified_diff(content[0], next_content[0], fromfile=f"{site}_before", tofile=f"{site}_after"))
                else:
                  payload = f"Site ({site}) change from '{content[0]}' to '{next_content[0]}'"

                if webhook_url:
                    httpx.post(webhook_url, data=payload)
                elif ntfy_channel:
                    httpx.post(f"https://ntfy.sh/{ntfy_channel}", data=payload)

        content = next_content
        succesive_errors = 0

        time.sleep(frequency)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--diff", action=argparse.BooleanOptionalAction,
                        help="send only diff instead of whole site if set")
    parser.add_argument("-s", "--site", type=str,
                        help="location of site to monitor")
    parser.add_argument("-z", "--selector", type=str,
                        help="selector to watch for the given site")
    parser.add_argument("-f", "--frequency", type=int, default=30,
                        help="amount of seconds to wait until next retry")
    parser.add_argument("-c", "--ntfy-channel", type=str,
                        help="the channel topic to use for ntfy.sh")
    parser.add_argument("-w", "--webhook-url", type=str,
                        help="the webhook URL to use for notifications")

    args = vars(parser.parse_args())

    main(**args)
