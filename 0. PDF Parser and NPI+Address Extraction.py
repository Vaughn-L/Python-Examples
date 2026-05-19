import time
from datetime import datetime

import io
import os
import re
import pandas as pd

path = r'\\brg-dc-fs1\DCDATA6\Cases\Active\(051382) Prisma Health Network Adequacy Analysis\Data Loading\UHC Provider Directory\\'
inputs = path + r'Inputs\\'
txt = path + r'Outputs\\NPI + Address\\PDF as String\\'
outputs = path + r'Outputs\\NPI + Address\\QC\\'

#####################################################################################################

#PURPOSE:
# Imports each text file that breaks out PDFs line-by-line
# Then splits the text into chunks by NPI # (using PI # due to weird scraping issue)
# Then cleans the NPI and stores it
# Then looks at the previous chunk for the telehealth indicator
# Then pulls all addresses at the subsequent chunk of the NPI section
# Then fills down NPI and other fields for each address
# Splits address field into component parts
# Saves down as txt files

#####################################################################################################

# Define the address pattern
address_pattern = r'(\d+[A-Za-z]* [\w\s,]+)\n([\w\s,]+ [A-Z]{2} \d{5})'
# r'((?:.*\n)*[\dA-Za-z# ,]+)\n([\w\s,#]+ [A-Z]{2} \d{5})' # This should pull all address lines before city-state-zip but causes code to take forever

# Define a regular expression to capture the street address, city, state, and zip code
parse_regex = r'^(.+) \|([\w\s,]+), ([A-Z]{2}) (\d{5})'

#####################################################################################################

for filename in os.listdir(txt):
    file = os.path.join(txt, filename)
    if file.find('Processed') != -1:

        start_time = time.time()
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Initialize empty lists for columns
        index_column = []
        npi_column = []
        telehealth_column = []
        address_column = []

        # Initialize variables
        current_npi = None        
	telehealth_indicator = None
        
        # Open the file for reading
        with open(file, "r") as f:
            # Read the entire contents of the file into a string
            file_contents = f.read()

        # Split the text into sections, each section starting with "NPI #"
        sections = re.split(r'(PI #\d+)', file_contents) # Accounting for dirty scrape where starts with PI # and not just NPI #
    
	# Figure out which pages contain NPI#s. The section before will be the telehealth indicator as a footnote (21) and the following section  will be the address info
        npi_index = []
        for index,element in enumerate(sections):
            if element.startswith("PI #"): 
                npi_index.append(index)
    
        # Iterate through the sections
        for i in npi_index:
        #for section in sections:
            current_npi = sections[i].replace('PI #','')  # Set the current NPI

	#Pull telehealth indicator using conservative ,21 or 21, (in theory, the footnote could be standalone)
            try:
                if sections[i-1][-50:].find(',21') != -1 or sections[i-1][-50:].find('21,') != -1:
                    telehealth_indicator = 'X'
                else:
                    telehealth_indicator = ''
            except:
                if sections[i-1][-25:].find(',21') != -1 or sections[i-1][-25:].find('21,') != -1:
                    telehealth_indicator = 'X'
                else:
                    telehealth_indicator = ''                  

	#Extract all addresses found for a given provider
            address_matches = re.findall(address_pattern, sections[i+1])  
            try:
                addresses = ['|'.join(match) for match in address_matches]
            except:
                addresses = '' 
               
	#Append results to lists for pushing into a dictionary
            index_column.append(i)
            npi_column.append(current_npi)
            address_column.append(addresses)
            telehealth_column.append(telehealth_indicator)

        # Create a dictionary to hold the data
        data = {'Index Column': [], 'NPI': [], 'Telehealth Indicator': [], 'address_columns': []}

        # All fields need to be filled down for the addresses (e.g., if a provider has 3 addresses, then the NPI in the first record needs to be filled down to the subsequent 2)
        for ind, npi, telehealth, addresses in zip(index_column, npi_column, telehealth_column, address_column):
            
            data['Index Column'].extend([ind] * len(addresses)) # This column helps de-bug by allowing us to write sections(i) to look at the individual chunks that weren't scraped properly
            data['NPI'].extend([npi] * len(addresses))
            data['Telehealth Indicator'].extend([telehealth] * len(addresses))
            data['address_columns'].extend(addresses)

        # Create the DataFrame
        df = pd.DataFrame(data)  

	#Remove rows missing an NPI -- this shouldn't happen
        df_npi = df.dropna(subset=['NPI'])

        df_npi['address_columns'] = df_npi['address_columns'].str.replace('\n',' ')

        # Use str.extract to extract the components of the address
        df_npi[['Street Address', 'City', 'State', 'Zip Code']] = df_npi['address_columns'].str.extract(parse_regex)

        # Drop the original address_columns
        df_npi = df_npi.drop('address_columns', axis=1)

        #Export dataframe
        df_npi.to_csv(outputs + filename.replace('.pdf','.txt'), index=None, sep='|', mode='a')