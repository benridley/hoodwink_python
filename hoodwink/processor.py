import json
import textwrap
from typing import cast
from bs4 import BeautifulSoup
import requests
from openai import OpenAI
from openai.types.chat import ChatCompletion
from tenacity import retry, wait_random_exponential, stop_after_attempt
import re
from hoodwink.ai_client import AIClient


# How many characters to check after an occurence of 'ingredient' for a common unit to identify ingredient lists.
UNIT_CHECK_LENGTH = 240
# How many characters to check for an end_marker, like the start of a comments section or instructions.
# Estimated as basically 80 lines of an ingredient list to approximate how far we should check.
END_CHECK_LENGTH = 40 * 80

common_units = [
    "g",
    "lbs",
    "cup",
    "cups",
    "tbsp",
    "tablespoons",
    "tsp",
    "oz",
    "ml",
    "mls",
    "l",
    "kg",
    "kgs",
    "qt",
    "pt",
    "gal",
    "gals",
    "pinch",
]

# Words often found in ingredients sections, but often not as a unit at the end of a digit.
common_words = [
    "cup",
    "tablespoon",
    "teaspoon",
    "slices",
    "pieces",
    "grams",
    "ounces",
    "gallons",
]

common_units_regex = re.compile(r"\b\d+\s*(" + "|".join(common_units) + r")\b")
common_words_refex = re.compile("(" + "|".join(common_words) + ")")

end_markers = [
    "instructions",
    "method",
    "comments",
    "directions",
    "preparation",
]

end_markers_regex = re.compile("(" + "|".join(end_markers) + ")")


def fetch_text(url: str) -> str:
    # Some recipe websites block the default requests user agent, so we hide it.
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "lxml")

    # Join all processed text with a newline separator, additional newline already added
    return soup.get_text(" ", strip=True)


def extract_ingredient_section(text: str) -> str:
    text_lower = text.lower()
    # Find the indices of all occurences of the word 'ingredients'
    indices = [m.start() for m in re.finditer("ingredients", text_lower)]

    # Check each of those occurences for the presence of a common unit close by.
    # We should see e.g. cup/s, tbsp, tsp, etc if it's a true list.
    # Store those indices.
    potential_start_indices: list[int] = []
    for index in indices:
        section = text_lower[index : index + UNIT_CHECK_LENGTH]
        if common_units_regex.findall(section) or common_words_refex.findall(section):
            potential_start_indices.append(index)

    # For each of those validated indices, check if we can find an end marker, like
    # the start of the 'method' section, 'comments' or the end of the page.
    terminated_sections = []
    unterminated_sections = []
    for index in potential_start_indices:
        section = text_lower[index : index + END_CHECK_LENGTH]
        # If we find end markers, we can stop processing and return up to that point.
        end_markers = [m.start() for m in end_markers_regex.finditer(section)]
        # Calculate the number of matches for common units and words
        unit_matches = len(common_units_regex.findall(section))
        word_matches = len(common_words_refex.findall(section))
        total_matches = unit_matches + word_matches

        if end_markers:
            terminated_sections.append((section[: end_markers[-1]], total_matches))
        if (index + END_CHECK_LENGTH) > len(text_lower):
            unterminated_sections.append((section, total_matches))

    # Return the section with the most hits (most 'dense' ingredient info)
    if terminated_sections:
        return max(terminated_sections, key=lambda x: x[1])[0]
    if unterminated_sections:
        return max(unterminated_sections, key=lambda x: x[1])[0]
    return ""


dodgy_key_count = 0


def extract_ingredients(recipe_text: str):
    ingredients_section = extract_ingredient_section(recipe_text)

    ai_client = AIClient("openai")
    system_prompt = textwrap.dedent(
        """
        You extract ingredients from recipes, a simplify them for a shopping list, then save them to the database. You
        must only call the save_ingredients function to do this. For instance, replace 'fettucine or other pasta' with
        'fettucine', noting alternatives in 'notes'. Omit preparation details, e.g., list 'prawns' instead of 'peeled
        and deveined prawns', with prep details in notes. Ignore alternative names after a slash and use the first or
        most specific name. Do not use slashes or alternatives in ingredient names. If no unit is specified, use "". For
        garnishes and toppings, if the recipe does not provide a quantity provide a resonable estimate.""",
    )
    messages = [{"role": "user", "content": ingredients_section}]
    resp = ai_client.tool_call_request(messages, system_prompt)
    # print(json.dumps(messages, indent=4))
    print(json.dumps(resp, indent=4))
    if "properties" in resp:
        return resp["properties"]
    return resp
