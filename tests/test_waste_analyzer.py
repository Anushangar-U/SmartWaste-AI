from agents.waste_analyzer.agent import analyze_complaint


def main():
    test_cases = [
        "Plastic bottles have been dumped beside the road for two days.",
        "Food waste has been left near a restaurant for one week and there is a strong smell.",
        "Someone dumped old batteries near the playground yesterday.",
        "The garbage collection bin is overflowing in the residential area.",
        "There is a large pile of food waste that has been there for three days.",
        "",
    ]

    for i, complaint in enumerate(test_cases, start=1):

        print("\n====================================")
        print(f"TEST COMPLAINT {i}")
        print("====================================")

        print("Complaint:")
        print(complaint)

        try:
            result = analyze_complaint(complaint)

            print("\nAgent 1 Result:")
            print(result.model_dump_json(indent=2))

        except ValueError as error:
            if not complaint.strip():
                print("\nPASS: Empty complaint correctly rejected.")
            else:
                print(f"\nValidation error: {error}")

        except Exception as error:
            print(f"\nTest failed: {error}")

if __name__ == "__main__":
    main()