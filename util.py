import os
from typing import List

def extract_code_from_local_project(project_path: str, extensions: List[str]) -> str:
    """
    Extracts code from a local project directory, concatenating it into a single string.
    Includes metadata and file separators for LLM context.
    Keeps comments intact and adds the file contents as is.
    """
    combined_code = ""
    for root, _, files in os.walk(project_path):
        for file in files:
            print("Processing file {}".format(file))
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code = f.read()
                        combined_code += f"// Filename: {filepath}\n"  # Metadata
                        combined_code += code + "\n\n// -------- File Separator --------\n\n" # Separator
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")


    return combined_code

def main():
    project_path = "app"  # Get path from the user

    # Define allowed extensions (customize as needed)
    ALLOWED_EXTENSIONS = ['.py', '.js', '.java', '.c', '.cpp', '.h', '.go', '.rs', '.ts', '.cs', '.php', '.rb', '.swift']  # Most Common

    extracted_code = extract_code_from_local_project(project_path, ALLOWED_EXTENSIONS)

    # PREPROCESSING (Important - Token Limit Handling)
    code_length = len(extracted_code)
    print(f"Original code length: {code_length}")

    # TRUNCATE (simplest, but least effective if the interesting part is cut off) - REMEMBER TO UNCOMMENT AND ADJUST
    # LLM_TOKEN_LIMIT = 4000 #tokens
    # extracted_code = extracted_code[:LLM_TOKEN_LIMIT * 3]  # Rough estimate: 1 token ~ 3-4 characters.

    # Split files into chunks with filenames and line numbers. (Best Approach)
    #    *(code for this is much more complex and beyond a basic example, suggest
    #      exploring libraries / code summarization techniques)*


    # Output (demonstration - adapt to your needs)
    with open("combined_code.txt", "w", encoding="utf-8") as outfile:
        outfile.write(extracted_code)
    print("Combined code written to combined_code.txt")



if __name__ == "__main__":
    main()