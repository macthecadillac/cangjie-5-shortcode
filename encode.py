import copy
import numpy as np
import json
import string


dp = 0.4  # deprioritization parameter
random_combo_undesirability = 10000
print("Deprioritization parameter: ", dp)


def weighed_shortcut_sequences(c, cj5, raw_score, segmented_positions):
    """
    本函數演算並列出基於引數之可行二級簡碼方案。引數是字元的五代倉頡碼。返回值列
    表中第一位為倉頡碼之首、尾碼，次者為首、次碼，再者為首、三碼，以此類推。
    List all possible two-character shortcut sequences for the given Cangjie 5
    encoding. The return list consists of, in this order, the first and last
    chars of the input sequence, the first and second chars, the first and third
    chars, ad infinitum.
    """
    combos = []
    combos.append((raw_score, cj5[0] + cj5[-1], (0, -1)))
    combos.append((raw_score * 0.999, cj5[0] + cj5[0], (0, 0)))
    combos.append((raw_score * 0.999, cj5[0] + cj5[1], (0, 1)))
    if segmented_positions is not None:
        try:
            combo = cj5[0] + cj5[segmented_positions[0]]
            if not segmented_positions[0] == 1:
                combos.append((raw_score * 0.998, combo, (100, 100)))
        except IndexError:
            print(c, cj5, segmented_positions)
    l = len(cj5)
    n = 10
    for i, c1 in enumerate(cj5):
        for j, c2 in enumerate(cj5):
            combo = c1 + c2
            # the sequences further down the list receive less priority
            combos.append((raw_score / (n + 1) ** dp,
                           combo,
                           (i, j if j < l - 1 else -1)))

    # sequences of one char from the input sequence + a random char
    x = n + 10
    for i, c1 in enumerate([cj5[0], cj5[-1], cj5[1:-1]]):
        for c2 in [*string.ascii_lowercase, ';', ',', '.']:
            combo = c1 + c2
            if i == 0:
                index = 0
            elif i == 1:
                index = -1
            else:
                index = i - 1
            combos.append((raw_score / x ** dp, combo, (index, -100)))
    # sequences of one random char + one char from the input sequence
    for c1 in [*string.ascii_lowercase, ';', ',', '.']:
        for i, c2 in enumerate([cj5[0], cj5[-1], cj5[1:-1]]):
            combo = c1 + c2
            if i == 0:
                index = 0
            elif i == 1:
                index = -1
            else:
                index = i - 1
            combos.append((raw_score / (x + i) ** dp, combo, (-100, index)))
    # truly random sequences
    x += random_combo_undesirability
    for c1 in [*string.ascii_lowercase, ';', ',', '.']:
        for c2 in [*string.ascii_lowercase, ';', ',', '.']:
            combo = c1 + c2
            combos.append((raw_score / x ** dp, combo, (-100, -100)))
    return combos


def position_test(seq, cj5, i, j):
    return seq[0] == cj5[i] and seq[1] == cj5[j]


frequency_data = np.genfromtxt('data/character-frequency.csv', delimiter=',',
                               skip_header=1, dtype=None, encoding='utf8')
character_frequency = dict(frequency_data)
total = sum(n for _, n in frequency_data)

# cj5_code = dict(np.genfromtxt('c5.yaml', delimiter='\t', dtype=None, encoding='utf8'))
# cj5_code = dict((entry[1], entry[0]) for entry in cj5_code_raw)

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

# with_multiple_encoding = dict((k, v) for k, v in cj5_code.items() if len(v) > 1)
# freq = list(sorted(((v, k) for k, v in character_frequency.items()), reverse=True))
# for f, c in freq:
#     if c in with_multiple_encoding:
#         print(c, with_multiple_encoding[c], f)

with open("data/segmentations.json", "r") as fh:
    segmentations = json.load(fh)

# We only make assignments to input sequences that are not occupied by any of
# the characters in Big5 and in GB2312 since Cangjie 5 officially supports the
# input of both simplified and traditional characters
with open('data/big5.txt', 'r') as fh:
    traditional_charset = fh.read()[:-1]
traditional_charset_cj5_code = (cj5_code[c] for c in traditional_charset)
used_combos_trad = set(seq for seqs in traditional_charset_cj5_code
                       for seq in seqs if len(seq) == 2)

with open('data/gb2312.txt', 'r') as fh:
    simplified_charset = fh.read()[:-1]
simplified_charset_cj5_code = (cj5_code[c] for c in simplified_charset)
used_combos_simp = set(seq for seqs in simplified_charset_cj5_code
                       for seq in seqs if len(seq) == 2)

merged_dict = {}
for c, f in character_frequency.items():
    cj5s = cj5_code[c]
    merged_dict[c] = (f, cj5s)

all_combos = set(a + b for a in [*string.ascii_lowercase, ';', ',', '.']
                 for b in [*string.ascii_lowercase, ';', ',', '.'])
available_combos = all_combos - used_combos_trad - used_combos_simp

# 以字頻及碼長之商為權，進行最佳化
# Set a score based on the product of the frequency and the length of the input
# sequence. We then optimize based on this score
common_chars_long_cj5 = list((f * min(len(s) for s in cj5s), cj5s, c)
                             for c, (f, cj5s) in merged_dict.items()
                             if 2 not in [len(s) for s in cj5s] and
                             1 not in [len(s) for s in cj5s])
common_chars_long_cj5.sort(reverse=True)

# 把位列常用字表首、次位的「的」與「是」排到「難」、「重」鍵上去
# Map the two most frequently used characters in the list of common characters
# onto "x" and "z" keys
shortcuts = {'x': ('的', (1000, 1000)), 'z': ('是', (1000, 1000))}
common_chars_long_cj5 = common_chars_long_cj5[2:]

# Now compute the weights for every possible shortcut sequence for every
# character on the shortlist
unassigned_chars = set(c for _, _, c in common_chars_long_cj5)
possible_shortcut_combos = []
for raw_score, cj5s, c in common_chars_long_cj5:
    try:
        segmented_positions = segmentations[c]
    except KeyError:
        segmented_positions = None
    for cj5 in cj5s:
        for score, seq, pos in weighed_shortcut_sequences(c, cj5, raw_score, segmented_positions):
            possible_shortcut_combos.append((score, cj5, seq, c, pos))
possible_shortcut_combos.sort(reverse=True)

# Assign shortcut sequences to the characters on the list based on the weights
for _, _, seq, c, pos in possible_shortcut_combos:
    if seq in available_combos and c in unassigned_chars:
        shortcuts[seq] = (c, pos)
        available_combos.remove(seq)
        unassigned_chars.remove(c)

# print("簡碼全表:\n", shortcuts)
print("簡碼共計: ", len(shortcuts))

# How well did we do?
print("Unused sequences: ", available_combos)
print("有二碼編碼、字頻最低的字: ",
      min(character_frequency[c[0]] for c in shortcuts.values()))

print("沒有二碼編碼、字頻最高的字: ",
      max(character_frequency[c] for _, _, c in common_chars_long_cj5
          if c not in (c for c, _ in shortcuts.values())))
print("特別單碼字: ", [('x', shortcuts['x']), ('z', shortcuts['z'])])
shortcuts.pop('x')
shortcuts.pop('z')

first_last = set((c, combo[0]) for c, combo in shortcuts.items() if combo[1] == (0, -1))
print("首、尾碼:\n", first_last)
print("共計: ", len(first_last))

doubled = set((c, combo[0]) for c, combo in shortcuts.items()
              if combo[1] == (0, 0) or
              combo[1] == (1, 1) or
              combo[1] == (2, 2) or
              combo[1] == (3, 3) or
              combo[1] == (4, 4) or
              combo[1] == (-1, -1))
print("重複任何一碼:\n", doubled)
print("共計: ", len(doubled))

first_second = set((c, combo[0]) for c, combo in shortcuts.items() if combo[1] == (0, 1))
print("首、次碼:\n", first_second)
print("共計: ", len(first_second))

first_first = set((c, combo[0]) for c, combo in shortcuts.items() if combo[1] == (100, 100))
print("字首、字身首碼:\n", first_first)
print("共計: ", len(first_first))

first_third = set((c, combo[0]) for c, combo in shortcuts.items() if combo[1] == (0, 2))
print("首、三碼:\n", first_third)
print("共計: ", len(first_third))

first_random = set((c, combo[0]) for c, combo in shortcuts.items()
                   if combo[1][0] == 0 and
                   (c, combo[0]) not in first_last | first_first | first_second | first_third | doubled)
print("首 + * 碼:\n", first_random)
print("共計: ", len(first_random))

second_random = set((c, combo[0]) for c, combo in shortcuts.items()
                    if combo[1][0] == 1 and (c, combo[0]) not in doubled)
print("次 + * 碼:\n", second_random)
print("共計: ", len(second_random))

last_random = set((c, combo[0]) for c, combo in shortcuts.items()
                  if combo[1][0] == -1 and (c, combo[0]) not in doubled)
print("尾 + * 碼:\n", last_random)
print("共計: ", len(last_random))


random_first = set((c, combo[0]) for c, combo in shortcuts.items()
                   if combo[1][1] == 0 and (c, combo[0]) not in
                   doubled | first_last | first_first | first_second | first_third |
                   first_random | second_random | last_random)
print("* + 首碼:\n", random_first)
print("共計: ", len(random_first))

random_second = set((c, combo[0]) for c, combo in shortcuts.items()
                    if combo[1][1] == 1 and (c, combo[0]) not in
                    doubled | first_last | first_first | first_second | first_third |
                    first_random | second_random | last_random | random_first)
print("* + 次碼:\n", random_second)
print("共計: ", len(random_second))

random_last = set((c, combo[0]) for c, combo in shortcuts.items()
                  if combo[1][1] == -1 and (c, combo[0]) not in
                  doubled | first_last | first_first | first_second | first_third |
                  first_random | second_random | last_random | random_first |
                  random_second)
print("* + 尾碼:\n", random_last)
print("共計: ", len(random_last))


random = set((c, combo[0]) for c, combo in shortcuts.items()
             if combo[1] == (-100, -100))

other_non_random = set((c, combo[0]) for c, combo in shortcuts.items()
                       if (c, combo[0]) not in first_last | first_first |
                       first_second | first_third | first_random |
                       second_random | random_last | random_first |
                       random_second | last_random | random | doubled)
print("其它未歸類簡碼:\n", other_non_random)
print("共計: ", len(other_non_random))


print("無理碼:\n", random)
print("共計: ", len(random))


print()
original_speed_index = sum(f * min(len(s) for s in cj5s) for _, (f, cj5s) in merged_dict.items())
average_seq_len_per_char = original_speed_index / total
print("倉頡五代平均碼長: ", average_seq_len_per_char)

new_encoding = dict((val[0], key) for key, val in shortcuts.items())
new_speed_index = 0
for c, (f, cj5s) in merged_dict.items():
    try:
        new_speed_index += len(new_encoding[c]) * f
    except KeyError:
        new_speed_index += min(len(s) for s in cj5s) * f
print("加入簡碼後平均碼長: ", new_speed_index / total)

print("預計增速: {}%"
      .format(np.round((1 - new_speed_index / original_speed_index) * 100, 2)))
