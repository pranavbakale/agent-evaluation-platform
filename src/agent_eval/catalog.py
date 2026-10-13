from __future__ import annotations

from functools import lru_cache

from .models import TaskSpec, TestVector


def _starter(function_name: str, signature: str) -> str:
    return f'def {function_name}({signature}):\n    """Implement the function described in the task."""\n    pass\n'


def _task(
    id: str,
    title: str,
    category: str,
    difficulty: str,
    summary: str,
    instructions: str,
    function_name: str,
    signature: str,
    reference_code: str,
    tests: list[tuple[str, list[object], object]],
) -> TaskSpec:
    return TaskSpec(
        id=id,
        title=title,
        category=category,
        difficulty=difficulty,
        summary=summary,
        instructions=instructions,
        function_name=function_name,
        signature=f"{function_name}({signature})",
        starter_code=_starter(function_name, signature),
        reference_code=reference_code.strip() + "\n",
        tests=tuple(TestVector(name=name, args=args, expected=expected) for name, args, expected in tests),
    )


@lru_cache(maxsize=1)
def get_catalog() -> tuple[TaskSpec, ...]:
    return (
        _task(
            "sum-numbers",
            "Sum Numbers",
            "Collections",
            "Easy",
            "Add every integer in a list.",
            "Return the sum of all values. An empty list returns 0. Do not mutate the input.",
            "sum_numbers",
            "values",
            """
def sum_numbers(values):
    return sum(values)
""",
            [
                ("positive values", [[1, 2, 3, 4]], 10),
                ("empty input", [[]], 0),
                ("mixed signs", [[-8, 3, 5, -2]], -2),
                ("single value", [[41]], 41),
            ],
        ),
        _task(
            "clamp-value",
            "Clamp a Value",
            "Numbers",
            "Easy",
            "Keep a number inside an inclusive range.",
            "Return lower when value is too small, upper when it is too large, and value otherwise.",
            "clamp",
            "value, lower, upper",
            """
def clamp(value, lower, upper):
    return max(lower, min(value, upper))
""",
            [
                ("inside range", [5, 0, 10], 5),
                ("below range", [-4, 0, 10], 0),
                ("above range", [18, 0, 10], 10),
                ("negative range", [-3, -8, -2], -3),
            ],
        ),
        _task(
            "clean-palindrome",
            "Clean Palindrome",
            "Strings",
            "Easy",
            "Recognize palindromes despite punctuation and casing.",
            "Return whether the alphanumeric characters read the same in both directions. Ignore case and all other characters.",
            "is_palindrome",
            "text",
            """
def is_palindrome(text):
    cleaned = ''.join(ch.lower() for ch in text if ch.isalnum())
    return cleaned == cleaned[::-1]
""",
            [
                ("classic phrase", ["A man, a plan, a canal: Panama!"], True),
                ("not a palindrome", ["deterministic"], False),
                ("empty after cleaning", ["..."], True),
                ("numeric text", ["10 01"], True),
            ],
        ),
        _task(
            "fizz-buzz-list",
            "Fizz Buzz List",
            "Control flow",
            "Easy",
            "Build a reusable Fizz Buzz result.",
            "Return strings for the integers from 1 through n. Multiples of 3 become Fizz, multiples of 5 become Buzz, and multiples of both become FizzBuzz.",
            "fizz_buzz",
            "n",
            """
def fizz_buzz(n):
    result = []
    for value in range(1, n + 1):
        if value % 15 == 0:
            result.append('FizzBuzz')
        elif value % 3 == 0:
            result.append('Fizz')
        elif value % 5 == 0:
            result.append('Buzz')
        else:
            result.append(str(value))
    return result
""",
            [
                ("first five", [5], ["1", "2", "Fizz", "4", "Buzz"]),
                ("includes fifteen", [15], ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"]),
                ("zero length", [0], []),
            ],
        ),
        _task(
            "unique-in-order",
            "Unique in Order",
            "Collections",
            "Easy",
            "Remove duplicates while retaining the first occurrence.",
            "Return a new list with each distinct item exactly once, in its original encounter order.",
            "unique_in_order",
            "values",
            """
def unique_in_order(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
""",
            [
                ("repeated integers", [[3, 1, 3, 2, 1]], [3, 1, 2]),
                ("already unique", [["a", "b", "c"]], ["a", "b", "c"]),
                ("empty input", [[]], []),
                ("all duplicates", [[7, 7, 7]], [7]),
            ],
        ),
        _task(
            "flatten-once",
            "Flatten Once",
            "Collections",
            "Easy",
            "Flatten one level of nested lists.",
            "Return a new list containing every item from each inner list in order. Flatten exactly one level.",
            "flatten_once",
            "groups",
            """
def flatten_once(groups):
    return [item for group in groups for item in group]
""",
            [
                ("regular groups", [[[1, 2], [3], [4, 5]]], [1, 2, 3, 4, 5]),
                ("empty groups", [[[], [1], []]], [1]),
                ("no groups", [[]], []),
                ("nested value retained", [[[[1]], [[2]]]], [[1], [2]]),
            ],
        ),
        _task(
            "chunk-list",
            "Chunk a List",
            "Collections",
            "Medium",
            "Split a list into fixed-width groups.",
            "Return consecutive chunks of at most size items. Size is always a positive integer; the final chunk may be shorter.",
            "chunk_list",
            "values, size",
            """
def chunk_list(values, size):
    return [values[index:index + size] for index in range(0, len(values), size)]
""",
            [
                ("uneven chunks", [[1, 2, 3, 4, 5], 2], [[1, 2], [3, 4], [5]]),
                ("exact chunks", [[1, 2, 3, 4], 2], [[1, 2], [3, 4]]),
                ("empty input", [[], 3], []),
                ("wide chunk", [[1, 2], 8], [[1, 2]]),
            ],
        ),
        _task(
            "word-frequency",
            "Word Frequency",
            "Strings",
            "Medium",
            "Count normalized words in a sentence.",
            "Return a dictionary of lowercase word counts. A word is one or more letters or digits; punctuation separates words.",
            "word_frequency",
            "text",
            """
import re

def word_frequency(text):
    counts = {}
    for word in re.findall(r'[a-z0-9]+', text.lower()):
        counts[word] = counts.get(word, 0) + 1
    return counts
""",
            [
                ("case normalization", ["Red blue RED"], {"red": 2, "blue": 1}),
                ("punctuation", ["one, two... two!"], {"one": 1, "two": 2}),
                ("empty input", [""], {}),
                ("digits", ["HTTP 200 and 200"], {"http": 1, "200": 2, "and": 1}),
            ],
        ),
        _task(
            "merge-sorted",
            "Merge Sorted Lists",
            "Algorithms",
            "Medium",
            "Merge two sorted lists without losing duplicates.",
            "Return one ascending list containing all values from both already-sorted inputs.",
            "merge_sorted",
            "left, right",
            """
def merge_sorted(left, right):
    result = []
    first = second = 0
    while first < len(left) and second < len(right):
        if left[first] <= right[second]:
            result.append(left[first])
            first += 1
        else:
            result.append(right[second])
            second += 1
    return result + left[first:] + right[second:]
""",
            [
                ("interleaved", [[1, 4, 8], [2, 3, 9]], [1, 2, 3, 4, 8, 9]),
                ("duplicates", [[1, 2, 2], [2, 3]], [1, 2, 2, 2, 3]),
                ("empty left", [[], [1, 5]], [1, 5]),
                ("both empty", [[], []], []),
            ],
        ),
        _task(
            "prime-check",
            "Prime Check",
            "Numbers",
            "Medium",
            "Determine whether an integer is prime.",
            "Return true only when n has exactly two positive divisors. Values below 2 are not prime.",
            "is_prime",
            "n",
            """
def is_prime(n):
    if n < 2:
        return False
    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 1
    return True
""",
            [
                ("small prime", [2], True),
                ("one", [1], False),
                ("composite", [49], False),
                ("larger prime", [97], True),
                ("negative", [-5], False),
            ],
        ),
        _task(
            "factorial",
            "Iterative Factorial",
            "Numbers",
            "Easy",
            "Calculate a non-negative integer factorial.",
            "Return n factorial. Inputs are non-negative integers and 0 factorial is 1.",
            "factorial",
            "n",
            """
def factorial(n):
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result
""",
            [
                ("zero", [0], 1),
                ("one", [1], 1),
                ("five", [5], 120),
                ("eight", [8], 40320),
            ],
        ),
        _task(
            "binary-search",
            "Binary Search",
            "Algorithms",
            "Medium",
            "Locate a value in a sorted list.",
            "Return an index whose value equals target, or -1 when target is absent. The input list is sorted ascending.",
            "binary_search",
            "values, target",
            """
def binary_search(values, target):
    low, high = 0, len(values) - 1
    while low <= high:
        middle = (low + high) // 2
        if values[middle] == target:
            return middle
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle - 1
    return -1
""",
            [
                ("middle item", [[1, 3, 5, 7, 9], 5], 2),
                ("first item", [[2, 4, 6], 2], 0),
                ("last item", [[2, 4, 6], 6], 2),
                ("missing item", [[2, 4, 6], 5], -1),
                ("empty list", [[], 1], -1),
            ],
        ),
        _task(
            "balanced-brackets",
            "Balanced Brackets",
            "Algorithms",
            "Medium",
            "Validate nested bracket pairs.",
            "Return whether (), [], and {} brackets are correctly paired and nested. Ignore non-bracket characters.",
            "balanced_brackets",
            "text",
            """
def balanced_brackets(text):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for character in text:
        if character in pairs.values():
            stack.append(character)
        elif character in pairs:
            if not stack or stack.pop() != pairs[character]:
                return False
    return not stack
""",
            [
                ("nested pairs", ["{[()]}"], True),
                ("crossed pairs", ["([)]"], False),
                ("unfinished pair", ["(()"], False),
                ("plain text", ["value + 2"], True),
                ("code fragment", ["items[call({})]"], True),
            ],
        ),
        _task(
            "rotate-right",
            "Rotate Right",
            "Collections",
            "Medium",
            "Rotate list values by a number of positions.",
            "Return a new list rotated to the right by steps. Steps may exceed the list length. Empty input returns an empty list.",
            "rotate_right",
            "values, steps",
            """
def rotate_right(values, steps):
    if not values:
        return []
    amount = steps % len(values)
    return values[-amount:] + values[:-amount] if amount else list(values)
""",
            [
                ("single rotation", [[1, 2, 3, 4], 1], [4, 1, 2, 3]),
                ("wrapped rotation", [[1, 2, 3, 4], 6], [3, 4, 1, 2]),
                ("zero rotation", [[1, 2, 3], 0], [1, 2, 3]),
                ("empty input", [[], 9], []),
            ],
        ),
        _task(
            "two-sum",
            "Two Sum",
            "Algorithms",
            "Medium",
            "Find the two positions that reach a target sum.",
            "Return the two zero-based indices as a list. Each case has exactly one solution; do not use an item twice.",
            "two_sum",
            "values, target",
            """
def two_sum(values, target):
    seen = {}
    for index, value in enumerate(values):
        needed = target - value
        if needed in seen:
            return [seen[needed], index]
        seen[value] = index
""",
            [
                ("first pair", [[2, 7, 11, 15], 9], [0, 1]),
                ("inside pair", [[3, 2, 4], 6], [1, 2]),
                ("repeated value", [[3, 3], 6], [0, 1]),
                ("negative value", [[-4, 8, 12, 1], 4], [0, 1]),
            ],
        ),
        _task(
            "slugify",
            "Slugify Text",
            "Strings",
            "Medium",
            "Turn a heading into a URL-friendly slug.",
            "Lowercase the text, replace runs of non-alphanumeric characters with one hyphen, and remove leading or trailing hyphens.",
            "slugify",
            "text",
            """
import re

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
""",
            [
                ("regular heading", ["Reliable Python Services"], "reliable-python-services"),
                ("punctuation run", ["Ship it: today!"], "ship-it-today"),
                ("outer punctuation", ["---Already clean---"], "already-clean"),
                ("empty input", [""], ""),
                ("digits retained", ["Version 2 API"], "version-2-api"),
            ],
        ),
        _task(
            "transpose-matrix",
            "Transpose Matrix",
            "Collections",
            "Medium",
            "Swap the rows and columns of a matrix.",
            "Return the transpose of a rectangular matrix. An empty matrix returns an empty list.",
            "transpose",
            "matrix",
            """
def transpose(matrix):
    if not matrix:
        return []
    return [list(column) for column in zip(*matrix)]
""",
            [
                ("square matrix", [[[1, 2], [3, 4]]], [[1, 3], [2, 4]]),
                ("wide matrix", [[[1, 2, 3], [4, 5, 6]]], [[1, 4], [2, 5], [3, 6]]),
                ("single row", [[[1, 2, 3]]], [[1], [2], [3]]),
                ("empty matrix", [[]], []),
            ],
        ),
        _task(
            "normalize-whitespace",
            "Normalize Whitespace",
            "Strings",
            "Easy",
            "Collapse uneven whitespace into single spaces.",
            "Return the words joined by one ordinary space. Treat spaces, tabs, and newlines as whitespace and trim both ends.",
            "normalize_whitespace",
            "text",
            """
def normalize_whitespace(text):
    return ' '.join(text.split())
""",
            [
                ("extra spaces", ["  one   two  "], "one two"),
                ("mixed whitespace", ["one\ttwo\nthree"], "one two three"),
                ("empty input", [""], ""),
                ("whitespace only", [" \n\t "], ""),
            ],
        ),
        _task(
            "run-length-encode",
            "Run-Length Encode",
            "Strings",
            "Medium",
            "Summarize consecutive character runs.",
            "Return a list of [character, count] pairs for each consecutive run. Preserve case and return an empty list for empty input.",
            "run_length_encode",
            "text",
            """
def run_length_encode(text):
    if not text:
        return []
    result = []
    current = text[0]
    count = 1
    for character in text[1:]:
        if character == current:
            count += 1
        else:
            result.append([current, count])
            current, count = character, 1
    result.append([current, count])
    return result
""",
            [
                ("several runs", ["aaabbc"], [["a", 3], ["b", 2], ["c", 1]]),
                ("separated repeat", ["abca"], [["a", 1], ["b", 1], ["c", 1], ["a", 1]]),
                ("empty input", [""], []),
                ("case preserved", ["AAaa"], [["A", 2], ["a", 2]]),
            ],
        ),
        _task(
            "top-k",
            "Top K Values",
            "Algorithms",
            "Medium",
            "Select the largest values in descending order.",
            "Return the k largest items sorted from largest to smallest. Keep duplicates. k is between 0 and the list length.",
            "top_k",
            "values, k",
            """
def top_k(values, k):
    return sorted(values, reverse=True)[:k]
""",
            [
                ("regular values", [[7, 1, 9, 3, 8], 3], [9, 8, 7]),
                ("duplicates", [[4, 4, 2, 9], 3], [9, 4, 4]),
                ("none requested", [[1, 2], 0], []),
                ("all requested", [[3, 1, 2], 3], [3, 2, 1]),
                ("negative values", [[-4, -1, -8], 2], [-1, -4]),
            ],
        ),
    )


def get_task(task_id: str) -> TaskSpec | None:
    return next((task for task in get_catalog() if task.id == task_id), None)

