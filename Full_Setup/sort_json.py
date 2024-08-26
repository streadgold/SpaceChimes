import json

def sort_json_file(file_path):
    # Read the existing data from the file
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Sort the data based on 'culmination_time'
    # Ensure all your dictionaries have the 'culmination_time' key. 
    data.sort(key=lambda x: x['culmination_time'])

    # Write the sorted data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    file_path = 'debris_data.json'  # Update this to your actual JSON file path
    sort_json_file(file_path)
    print(f"The file '{file_path}' has been sorted by culmination time.")

