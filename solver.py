import os
import requests
import re
from collections import Counter


class DictionaryDownloader:
    def __init__(self, url: str, save_dir: str = "dict", filename: str = "words.txt"):
        self.url = url
        self.save_dir = save_dir
        self.filename = filename
        os.makedirs(self.save_dir, exist_ok=True)

    def download(self):
        """Download the dictionary from the given url and save it to
        the given directory under the given filename.

        Prints a message on success or failure.

        :raises requests.RequestException: if there is an error downloading
            the file.
        """
        save_path = os.path.join(self.save_dir, self.filename)
        try:
            print(f"Downloading dictionary from {self.url} ...")
            response = requests.get(self.url)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"Saved dictionary to {save_path}")
        except requests.RequestException as e:
            print(f"Error downloading file: {e}")


class WordFilter:
    def __init__(self, input_path="dict/words.txt", output_path="dict/words_filtered.txt"):
        self.input_path = input_path
        self.output_path = output_path
        self.pattern = re.compile(r"^[a-z]{5}$")

    def filter_and_save(self):
        """
        Filters a list of words from the input file, keeping only those that match
        the specified pattern (5-letter lowercase words), and saves the filtered
        list in sorted order to the output file. If the input file is not found,
        prints a message and exits.

        The function ensures that the words are unique and sorted alphabetically
        before writing them to the output file.

        Prints the number of words saved to the output file.

        :raises FileNotFoundError: if the input file does not exist.
        """

        if not os.path.exists(self.input_path):
            print(f"File {self.input_path} not found!")
            return

        words_set = set()

        with open(self.input_path, "r", encoding="utf-8") as infile:
            for line in infile:
                word = line.strip().lower()
                if self.pattern.match(word):
                    words_set.add(word)

        sorted_words = sorted(words_set)

        with open(self.output_path, "w", encoding="utf-8") as outfile:
            for word in sorted_words:
                outfile.write(word + "\n")

        print(f"Filtered words saved to {self.output_path}, total {len(sorted_words)} words.")


class WordleSolver:
    def __init__(self, words):
        self.words = words

    def filter_candidates(self, known_pattern, unknowns, excluded_letters):
        """
        Filter the list of words based on the given clues.

        Parameters:
            known_pattern (list[str]): List of length 5, where each element is either
                a lowercase letter or None. If a letter is given, it must be in the
                corresponding position in the word.
            unknowns (list[tuple[int, str]]): List of tuples, where the first element
                is the index of the letter in the word and the second element is the
                letter. The letter must appear in the word, but not in the given
                position.
            excluded_letters (list[str]): List of letters that should not appear in
                the word.

        Returns:
            list[str]: The filtered list of words.
        """
        pattern = "".join([ch if ch else "." for ch in known_pattern])
        print(f"Regex Pattern: {pattern}")
        regex = re.compile(pattern)

        candidates = [w for w in self.words if regex.match(w)]
        print(f"After Known Positions: {len(candidates)} words")

        for idx, letter in unknowns:
            candidates = [w for w in candidates if letter in w and w[idx] != letter]
        if unknowns:
            print(f"After Unknown Positions: {len(candidates)} words")

        if excluded_letters:
            # Identify letters that are both excluded and present in knowns/unknowns
            confirmed_letters = {ch for ch in known_pattern if ch} | {pair[1] for pair in unknowns}

            filtered_candidates = []
            for w in candidates:
                keep = True
                for ch in excluded_letters:
                    if ch in confirmed_letters:
                        # Special case: The letter is in the word, but this specific
                        # instance was grey. This implies the word should not have
                        # MORE occurrences of 'ch' than already confirmed.
                        count_in_clues = list(known_pattern).count(ch) + [p[1] for p in unknowns].count(ch)
                        if w.count(ch) > count_in_clues:
                            keep = False
                            break
                    else:
                        # Normal case: The letter is not in the word at all
                        if ch in w:
                            keep = False
                            break
                if keep:
                    filtered_candidates.append(w)

            candidates = filtered_candidates
            print(f"Excluded Letters: {excluded_letters}")
            print(f"After Excluded Letters: {len(candidates)} words")

        return candidates


class LetterFrequencyAnalyzer:
    def __init__(self, input_path="dict/words_filtered.txt"):
        self.input_path = input_path
        self.frequencies = Counter()

    def analyze(self):
        """
        Analyzes the frequency of letters in the filtered word list.
        Each letter is only counted once per word (i.e., no double-counting within a word).
        Stores the result in self.frequencies.
        """
        if not os.path.exists(self.input_path):
            print(f"File {self.input_path} not found!")
            return

        with open(self.input_path, "r", encoding="utf-8") as file:
            for line in file:
                word = line.strip()
                unique_letters = set(word)
                self.frequencies.update(unique_letters)

        total = sum(self.frequencies.values())
        print(f"\nLetter Frequencies (each letter counted once per word):")
        for letter, count in self.frequencies.most_common():
            weight = count / total * 100
            print(f"{letter}: {count} ({weight:.2f}%)")

    def suggest_best_words(self, word_list=None, top_n=20):
        """
        Suggest top words based on letter frequency weights.

        If word_list is not provided, words will be read from self.input_path.

        Parameters:
            word_list (list[str], optional): List of words to score. If None, reads from input file.
            top_n (int): Number of top words to return.

        Returns:
            list[tuple[str, float]]: List of (word, score), sorted by score descending.
        """
        # If no word list provided, read from input file
        if word_list is None:
            if not os.path.exists(self.input_path):
                print(f"File {self.input_path} not found!")
                return []
            with open(self.input_path, "r", encoding="utf-8") as f:
                word_list = [line.strip() for line in f if line.strip()]

        # Compute score of each word based on letter frequency
        scored_words = []
        for word in word_list:
            unique_letters = set(word)
            score = sum(self.frequencies.get(ch, 0) for ch in unique_letters)
            scored_words.append((word, score))

        scored_words.sort(key=lambda x: x[1], reverse=True)
        return scored_words[:top_n]


if __name__ == "__main__":
    dict_url = "https://github.com/TitanComputer/wordle-list/raw/refs/heads/main/words"

    downloader = DictionaryDownloader(dict_url)
    downloader.download()
    wf = WordFilter()
    wf.filter_and_save()
    analyzer = LetterFrequencyAnalyzer()
    analyzer.analyze()

    # top_words = analyzer.suggest_best_words()
    # for word, score in top_words:
    #     print(f"{word}: {score:.2f}")

    # custom_words = ["crane", "slate", "ghost"]
    # top_custom = analyzer.suggest_best_words(word_list=custom_words, top_n=3)
    # for word, score in top_custom:
    #     print(f"{word}: {score:.2f}")
