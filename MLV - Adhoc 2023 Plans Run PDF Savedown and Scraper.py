### CHANGED INPUTS LINE TO ONLY INCLUDE ADDITIONAL ONES (FROM 10/27)

import io
import os
import time
from datetime import datetime
from PyPDF2 import PdfReader
import pdfquery
from pyquery import PyQuery
from lxml import etree
import re
import pandas as pd
from bs4 import BeautifulSoup

path = r'\\brg-dc-fs1\DCDATA6\Cases\Active\(051382) Prisma Health Network Adequacy Analysis\Data Loading\UHC Provider Directory\\'
inputs = path + r'Inputs\\2023 Plans\\'
txt = path + r'Outputs\\NPI + Address\\PDF as String\\2023 Plans\\'
outputs = path + r'Outputs\\NPI + Address\\2023 Plans\\'

#####################################################################################################

# Define the address pattern
address_pattern = r'(\d+[A-Za-z]* [\w\s,]+)\n([\w\s,]+ [A-Z]{2} \d{5})'

# Define a regular expression to capture the street address, city, state, and zip code
regex = r'^(.+) \|([\w\s,]+), ([A-Z]{2}) (\d{5})'

#####################################################################################################

for filename in os.listdir(inputs):
    file = os.path.join(inputs, filename)
    if file.find('.pdf') != -1:

        start_time = time.time()
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        #Combine all pages into a single string
        raw_pages = ''
        all_pages = ''

        # Initialize empty lists for NPI and Address columns
        npi_column = []
        address_column = []
        new_address_column = []

        # Initialize NPI
        current_npi = None

        # Pull PDF metadatas
        pdf_file = PdfReader(file)
        num_pages = len(pdf_file.pages)

        # Create a PDFQuery object and load the entire PDF
        pdf = pdfquery.PDFQuery(file)

        ############################################################################################
        #NOTE THIS LINE OF CODE TAKES THE LONGEST TO RUN SINCE THESE FILES ARE HUGE
        ############################################################################################
        pdf.load()
        ##############################################

        # Extract the XML content from the loaded PDF
        pdf.tree

        # Loop through each page and extract the XML content
        for page_num in range(num_pages):
            
            if page_num % 100 == 0:
                print(filename,[page_num],"--- %s seconds ---" % (time.time() - start_time))
            
            # Find all text elements within the specific page
            page_elements = str(pdf.pq('LTPage[pageid="%d"]' % page_num))

            # Parse the input text using BeautifulSoup
            soup = BeautifulSoup(page_elements, 'html.parser')

            # Find all LTTextLineHorizontal elements
            elements = soup.find_all('lttextlinehorizontal')

            # Create a function to extract x0 and y0 values from an element
            def get_coordinates(element):
                x0 = float(element['x0'])
                y0 = float(element['y0'])
                return x0, -y0, element.text # Need to sort y0 descending

            # Create a dictionary to count the frequency of each x0 value
            x0_frequency = {}
            for element in elements:
                x0 = get_coordinates(element)[0]
                if x0 in x0_frequency:
                    x0_frequency[x0] += 1
                else:
                    x0_frequency[x0] = 1

            # Find the top three most frequent x0 values
            top_x0 = [x for x, _ in sorted(x0_frequency.items(), key=lambda item: item[1], reverse=True)[:3]]

            # Create a mapping of x0 values to their closest value from the top three frequencies
            x0_mapping = {x0: min(top_x0, key=lambda x: abs(x - x0)) for x0 in x0_frequency.keys()}

            # Reassign x0 based on the mapping
            for element in elements:
                x0, y0, text = get_coordinates(element)
                new_x0 = x0_mapping[x0]
                element['x0'] = str(new_x0)

            # Sort the elements by x0 in ascending order
            sorted_elements = sorted(elements, key=get_coordinates)
            
            # Extract the desired text from the sorted elements
            result = [element.text for element in sorted_elements]

            result_str = '\n'.join([str(elem) for elem in result])

            raw_pages = raw_pages + '~~~PAGE NUMBER ' + str(page_num) + ' ~~~' + str(elements)
            all_pages = all_pages + '\n' + '~~~PAGE NUMBER ' + str(page_num) + ' ~~~' + result_str

 
        raw_text_file = open(txt + 'Raw - ' + filename.replace('.pdf','.txt'), 'w')
        raw_text_file.write(raw_pages)
        raw_text_file.close()

        text_file = open(txt + 'Processed - ' + filename.replace('.pdf','.txt'), 'w')
        text_file.write(all_pages)
        text_file.close()

        # Split the text into sections, each section starting with "NPI #"
        sections = re.split(r'(PI #\d+)', all_pages) # Accounting for dirty scrape where starts with PI # and not just NPI #

        # Iterate through the sections
        for section in sections:
            if section.startswith("PI #"): 
                current_npi = section.replace('PI #','')  # Set the current NPI
            else:
                if current_npi:
                    npi_column.append(current_npi)
                    address_column.append(section)

        for a in address_column:
            # Find all matches in the text
            address_matches = re.findall(address_pattern, a)
            try:
                addresses = ['|'.join(match) for match in address_matches]
            except:
                addresses = ''
            new_address_column.append(addresses)

        print(filename,"--- %s seconds ---" % (time.time() - start_time))

        # Create a dictionary to hold the data
        data = {'NPI': [], 'address_columns': []}

        # Iterate through NPIs and corresponding addresses
        for npi, addresses in zip(npi_column, new_address_column):
            data['NPI'].extend([npi] * len(addresses))
            data['address_columns'].extend(addresses)

        # Create the DataFrame
        df = pd.DataFrame(data)

        # Use str.extract to extract the components
        df[['Street Address', 'City', 'State', 'Zip Code']] = df['address_columns'].str.extract(regex)

        # Drop the original address_columns
        df = df.drop('address_columns', axis=1)

        #Export dataframe
        df.to_csv(outputs + filename.replace('.pdf','.txt'), index=None, sep='|', mode='a')