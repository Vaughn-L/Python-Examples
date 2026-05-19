import re
import pandas as pd

path = r'\\brg-dc-fs1\DCDATA6\Cases\Active\(051382) Prisma Health Network Adequacy Analysis\Data Loading\UHC Provider Directory\Intermediate Files\\'
df = pd.read_csv(path + r'raw_uhc_provider_directory_npi_addresses.txt', sep='\t', header=None, names=['NPI','Street','City','State','ZIP'])

def extract_address_info(address):
    # Define regular expressions to match the building number and street address
    building_pattern = r"\b\d+\w*\s+(?=\S)|\d+\w*\b"
    street_pattern = r"^(.*?)(\b(?:Apartment|Apt|Ste|Suite|Unit|Building|Bldg|Floor|Fl|Room|Rm|Spc|Ofc)\s+(\S+))"
 
    # Find the building number
    building_match = re.search(building_pattern, address)
    building_number = building_match.group(0) if building_match else ""

    # Extract the street and suite information
    match = re.search(street_pattern, address)
    if match:
        street_name = match.group(1).strip()  # Remove leading/trailing spaces
        street_name = re.sub(building_number, "", street_name) # Remove the building number from the street name
        suite_info = match.group(2)
    else:
        street_name = address.strip()  # Remove leading/trailing spaces
        street_name = re.sub(building_number, "", street_name) # Remove the building number from the street name
        suite_info = ""

    return building_number, street_name, suite_info

# Apply the function to the "address" column and split the results into new columns
df[["Building_Number", "Street_Name", "Apartment_Suite_Number"]] = df["Street"].apply(extract_address_info).apply(pd.Series)

df.to_csv(path + r'parsed_uhc_provider_directory_npi_addresses.txt', index=False, sep='\t')