import asyncio
import json
import re
import string

import aiohttp
from bs4 import BeautifulSoup
# import numpy as np


cangjie_root_map = dict((k, v) for k, v in
                        zip("日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜重",
                            string.ascii_lowercase))

# cj5_code = dict(np.genfromtxt('c5.yaml', delimiter='\t', dtype=None, encoding='utf8'))
cj5_code = dict()
with open('data/c5.yaml', 'r') as fh:
    lines = fh.readlines()

for line in lines:
    [char, cj5] = line.split('\t')
    if char in cj5_code:
        cj5_ = cj5_code[char]
        cj5_code[char] = [cj5.strip(), *cj5_]
    else:
        cj5_code[char] = [cj5.strip()]


def segmentation(char, html):
    char_cj5 = cj5_code[char]
    # Some are false negatives. However, false negatives are not a bug of this
    # script, but a result of the character being very obscure that the dataset
    # doesn't have it.
    if not (re.search("{}是分體字".format(char), html) is None and
            re.search("「{}」是分體字".format(char), html) is None):
        # Parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        # Extract the divs with Chinese characters grouped
        groups = []
        different_gen5 = True
        for center_div in soup.find_all("div", class_="text-center"):
            group = []
            for span in center_div.find_all("span", class_=re.compile("五")):
                # Extract the Chinese characters in the current div
                # The text comes out to be 第n碼x, where x is the char we're after
                if len(span.text.strip()) == 4:
                    characters = span.text.strip()[-1]
                    group.append(characters)
            if group:
                groups.append(group)
        if not groups:
            different_gen5 = False
            for center_div in soup.find_all("div", class_="text-center"):
                group = []
                for span in center_div.find_all("span"):
                    # Extract the Chinese characters in the current div
                    # The text comes out to be 第n碼x, where x is the char we're after
                    if len(span.text.strip()) == 4:
                        characters = span.text.strip()[-1]
                        group.append(characters)
                if group:
                    groups.append(group)

        if not different_gen5:
            n = len(groups)
            if groups[:n // 2] == groups[n // 2:]:
                segmented_encoding = groups[n // 2:]
            else:
                segmented_encoding = groups
        else:
            segmented_encoding = groups

        try:
            if not ''.join([cangjie_root_map[c] for c in sum(segmented_encoding, [])]) in char_cj5:
                if segmented_encoding != groups:
                    print(char, segmented_encoding, groups, char_cj5)
                else:
                    print(char, groups, char_cj5)
        except KeyError:
            print(char, segmented_encoding)
        try:
            segmentation = (len(segmented_encoding[0]), len(sum(segmented_encoding[1:], [])))
            return segmentation
        except IndexError:
            print(char, segmented_encoding)


async def fetch(session, char):
    url = 'https://www.hkcards.com/cj/cj-char-{}.html'.format(char)
    async with session.get(url) as response:
        res = await response.text()
        return char, res


async def fetch_urls(chars, rate_limit=5):
    results = {}
    semaphore = asyncio.Semaphore(rate_limit)  # Limit to `rate_limit` requests per second

    async def limited_fetch(char):
        async with semaphore:
            return await fetch(session, char)

    async with aiohttp.ClientSession() as session:
        tasks = [limited_fetch(char) for char in chars]
        for task in asyncio.as_completed(tasks):
            char, html = await task
            results[char] = html

    return results


# Run the async function to fetch URLs
if __name__ == "__main__":
    # frequency_data = np.genfromtxt('character-frequency.csv', delimiter=',',
    #                                skip_header=1, dtype=None, encoding='utf8')
    # character_frequency = dict(frequency_data)
    # frequent_chars = list(c for c, _ in frequency_data)

    # results = asyncio.run(fetch_urls(frequent_chars, rate_limit=5))
    # with open("fetched_html.json", "w") as fh:
    #     json.dump(results, fh)
    with open("data/fetched_html.json", "r") as fh:
        results = json.load(fh)

    # print(results['倌'])
    # print(segmentation('倌', results['倌']))
    segmentations = {}
    for i, (char, html) in enumerate(results.items()):
        print("Processing {}".format(i), end='\r')
        seg = segmentation(char, html)
        if seg is not None:
            segmentations[char] = seg
        # if i >= 200:
        #     break
    # segmentations = dict((char, segmentation(char, html)) for char, html in results.items())
    with open("data/segmentations.json", "w") as fh:
        json.dump(segmentations, fh)
