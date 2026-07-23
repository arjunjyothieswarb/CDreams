#!/usr/bin/env python3
"""
hazop_phrase_generator.py

A HAZOP (Hazard and Operability Study) deviation phrase generator.

HAZOP studies apply standard "guidewords" (No, More, Less, Reverse, etc.)
to process parameters (Flow, Temperature, Pressure, Level, Composition, etc.)
to systematically generate deviation phrases such as "No Flow" or
"More Temperature". This script stores a knowledge base of parameters and
their applicable guidewords, generates standard deviation phrases for a
given parameter, and lets the user extend the knowledge base with custom
parameters and guidewords.
"""

import argparse
import sys


class HazopPhraseGenerator:
    """Stores process parameters and guidewords, and generates deviation phrases."""

    # Standard HAZOP guidewords commonly used in industrial process safety
    # studies (IEC 61882 / typical HAZOP practice). Not every guideword is
    # meaningful for every parameter, so each parameter lists only the
    # guidewords that conventionally apply to it.
    DEFAULT_KNOWLEDGE_BASE = {
        "Flow": ["No", "More", "Less", "Reverse", "Misdirected"],
        "Temperature": ["No", "More", "Less"],
        "Pressure": ["No", "More", "Less"],
        "Level": ["No", "More", "Less"],
        "Composition": ["More", "Less", "Part of", "Other Than"],
        "Reaction": ["No", "More", "Less", "Reverse", "Other Than"],
        "Mixing": ["No", "More", "Less"],
        "Time": ["Early", "Late", "Before", "After"],
        "Phase": ["More", "Less", "Other Than"],
    }

    def __init__(self):
        # Store a fresh copy so class-level defaults are never mutated
        self.knowledge_base = {
            param: list(guidewords)
            for param, guidewords in self.DEFAULT_KNOWLEDGE_BASE.items()
        }

    def add_parameter(self, parameter, guidewords):
        """Add a new custom parameter (or extend an existing one) with guidewords.

        Args:
            parameter: Name of the process parameter, e.g. "Speed".
            guidewords: List of guideword strings, e.g. ["No", "More", "Less"].
        """
        parameter = parameter.strip()
        cleaned_guidewords = [gw.strip() for gw in guidewords if gw.strip()]

        if parameter in self.knowledge_base:
            # Extend without creating duplicates
            existing = self.knowledge_base[parameter]
            for gw in cleaned_guidewords:
                if gw not in existing:
                    existing.append(gw)
        else:
            self.knowledge_base[parameter] = cleaned_guidewords

    def generate_phrases(self, parameter):
        """Generate standard deviation phrases for a given parameter.

        Args:
            parameter: The process parameter to generate deviations for.

        Returns:
            A list of deviation phrase strings, e.g. ["No Flow", "More Flow", ...].

        Raises:
            KeyError: If the parameter is not present in the knowledge base.
        """
        if parameter not in self.knowledge_base:
            raise KeyError(
                f"Parameter '{parameter}' not found in knowledge base. "
                f"Available parameters: {', '.join(sorted(self.knowledge_base))}"
            )

        guidewords = self.knowledge_base[parameter]
        return [f"{guideword} {parameter}" for guideword in guidewords]

    def list_parameters(self):
        """Return a sorted list of all known parameters."""
        return sorted(self.knowledge_base)


def print_phrases(generator, parameter, out=sys.stdout):
    """Print the deviation phrases for a parameter, or an error message."""
    try:
        phrases = generator.generate_phrases(parameter)
        print(f"\nDeviation phrases for '{parameter}':", file=out)
        for phrase in phrases:
            print(f"  - {phrase}", file=out)
    except KeyError as exc:
        print(f"\nError: {exc}", file=out)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate standard HAZOP deviation phrases for a process parameter."
    )
    parser.add_argument(
        "parameter",
        nargs="?",
        help="Process parameter to generate deviation phrases for (e.g. Flow).",
    )
    parser.add_argument(
        "--add-parameter",
        metavar="NAME",
        help="Add a custom parameter to the knowledge base.",
    )
    parser.add_argument(
        "--guidewords",
        metavar="GW",
        nargs="+",
        help="Guidewords to associate with --add-parameter (space separated).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all parameters currently in the knowledge base.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a built-in demonstration with several parameters, including a custom one.",
    )
    parser.add_argument(
        "--save-sample",
        metavar="FILE",
        nargs="?",
        const="sample_output.txt",
        default=None,
        help="Write a set of test-case results to FILE (default: sample_output.txt).",
    )
    return parser


def run_demo(out=sys.stdout):
    """Demonstrate the generator with standard and custom parameters."""
    generator = HazopPhraseGenerator()

    print("=== HAZOP Phrase Generator Demo ===", file=out)

    # 1. Standard parameter: Flow
    print_phrases(generator, "Flow", out)

    # 2. Standard parameter: Temperature
    print_phrases(generator, "Temperature", out)

    # 3. Standard parameter: Pressure
    print_phrases(generator, "Pressure", out)

    # 4. Custom parameter added by the user
    generator.add_parameter("Agitator Speed", ["No", "More", "Less", "Reverse"])
    print_phrases(generator, "Agitator Speed", out)

    print("\nAll known parameters:", file=out)
    print(", ".join(generator.list_parameters()), file=out)


def generate_sample_output(path="sample_output.txt"):
    """Run the script through several test cases and write the results to a file.

    This is what produces the sample_output.txt deliverable. It exercises:
      - three standard parameters (Flow, Temperature, Pressure)
      - one custom parameter added at runtime (Agitator Speed)
      - the --list functionality
      - error handling for an unrecognized parameter

    Args:
        path: File path to write the sample output to.
    """
    generator = HazopPhraseGenerator()

    with open(path, "w") as f:
        f.write("HAZOP Phrase Generator - Sample Output\n")
        f.write("=" * 40 + "\n\n")

        f.write("Test 1: Standard parameter - Flow\n")
        f.write("-" * 40 + "\n")
        print_phrases(generator, "Flow", out=f)
        f.write("\n")

        f.write("Test 2: Standard parameter - Temperature\n")
        f.write("-" * 40 + "\n")
        print_phrases(generator, "Temperature", out=f)
        f.write("\n")

        f.write("Test 3: Standard parameter - Pressure\n")
        f.write("-" * 40 + "\n")
        print_phrases(generator, "Pressure", out=f)
        f.write("\n")

        f.write("Test 4: Custom parameter - Agitator Speed\n")
        f.write("-" * 40 + "\n")
        generator.add_parameter("Agitator Speed", ["No", "More", "Less", "Reverse"])
        f.write("Added custom parameter 'Agitator Speed' with guidewords: "
                "No, More, Less, Reverse\n")
        print_phrases(generator, "Agitator Speed", out=f)
        f.write("\n")

        f.write("Test 5: Listing all known parameters\n")
        f.write("-" * 40 + "\n")
        f.write(", ".join(generator.list_parameters()) + "\n\n")

        f.write("Test 6: Unrecognized parameter (error handling)\n")
        f.write("-" * 40 + "\n")
        print_phrases(generator, "Viscosity", out=f)

    print(f"Sample output written to '{path}'")


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    generator = HazopPhraseGenerator()

    if args.add_parameter:
        generator.add_parameter(args.add_parameter, args.guidewords or [])
        print(f"Added parameter '{args.add_parameter}' with guidewords: "
              f"{', '.join(args.guidewords) if args.guidewords else '(none)'}")

    if args.list:
        print("Known parameters:")
        print(", ".join(generator.list_parameters()))

    if args.save_sample:
        generate_sample_output(args.save_sample)
        return

    if args.demo:
        run_demo()
        return

    if args.parameter:
        print_phrases(generator, args.parameter)
    elif not args.list and not args.add_parameter:
        # No arguments given at all -> generate the sample output file by default
        generate_sample_output()


if __name__ == "__main__":
    main()