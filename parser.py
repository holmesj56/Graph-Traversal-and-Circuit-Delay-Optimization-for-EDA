import csv
import re
import pandas as pd
import numpy as np
import argparse
import sys

parser = argparse.ArgumentParser(description="to process both .bench file and .lib file .")
parser.add_argument('--read_ckt', type=str)
parser.add_argument('--delays', action='store_true')
parser.add_argument('--slews', action='store_true')
parser.add_argument('--read_nldm', type=str)
args = parser.parse_args()


type = None
if args.delays:
    type='delays'
elif args.slews:
    type='slews'



if args.read_ckt:
    txt = open("ckt_details.txt", "w+")
    file = args.read_ckt

    def count_gates(file_path):              # counting each of the gates
        gate_counts = {
                        "INPUT": 0,
                        "OUTPUT": 0,
                        "NAND": 0,
                        "NOR": 0,
                        "AND": 0,
                        "OR": 0,
                        "NOT": 0,
                        "BUFF": 0,
        }
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue  # Skiping the lines starting with #
                elif line.startswith('INPUT'):
                    gate_counts["INPUT"] += 1  # if it starts with INPUT count is added similarly for output 
                elif line.startswith('OUTPUT'):
                    gate_counts["OUTPUT"] += 1
                else:
                    for gate in ["NAND", "NOR", "AND", "OR", "NOT", "BUFF"]:
                        if gate in line: # gates compared in every line 
                            gate_counts[gate] += 1
                            break  

        return gate_counts

    gate_counts = count_gates(file)
    for gate, count in gate_counts.items():
        if count > 0:
            if gate=='INPUT':
                #print(f"{"primary inputs"}: {count}")
                txt.write(f"primary inputs:\t{count}\n")
            elif gate=='OUTPUT':
                #print(f"{"primary outputs"}: {count}")
                txt.write(f"primary outputs:  {count}\n")
            else:
                txt.write(f"{count} {gate} gates\n")




    # finding the patterns of outputs  and inputs 
    def read_io(file_path, patt):
        pattern = rf'{patt}\(([^)]+)\)'
        found = []
        with open(file_path, 'r') as f:
            for line in f:
                match = re.findall(pattern, line)
                found.extend(match)
        return found

    inputs = read_io(file, "INPUT")
    outputs = read_io(file, "OUTPUT")
    #converting to dataframe for easy access 

    df_input = pd.DataFrame(inputs, columns=['Inputs'])
    df_output = pd.DataFrame(outputs, columns=['Output'])
    print(df_input)
    print(df_output)

    # computing fanin and fanout values 
    def read_fanin_fanout(file_path):
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                if '=' in line:
                    parts = line.split('=')
                    if len(parts) == 2:
                        gate_output, gate_info = parts
                        gate_output = gate_output.strip()
                        gate_type, inputs = re.match(r"(\w+)\((.*?)\)", gate_info.strip()).groups()#  each line is split into 2 
                        inputs_list = [inp.strip() for inp in inputs.split(',')]
                        data.append({"Out": gate_output, "Gate": gate_type, "Fanin": inputs_list, "Fanout": []}) #data at each level is appended to the list data
        # Computing  fanout
        for index, row in enumerate(data):
            for target in data:
                if row['Out'] in target['Fanin']:
                    row['Fanout'].append(target['Out'])
            if not row['Fanout']:  # cheching fanout list empty
                row['Fanout'] = 'OUTPUT'
        return data

    data = read_fanin_fanout(file)
    df_fanin_fanout = pd.DataFrame(data)
    print(df_fanin_fanout)

    #df_fanin_fanout['Fanout'] = df['Fanout'].apply(lambda x: [x] if not isinstance(x, list) else x)

    for i, row in df_fanin_fanout.iterrows():
        if isinstance(row['Fanout'], list): #adding the string to a single line and joining if not empty 
            fanout_str = ','.join([f"{df_fanin_fanout.loc[df_fanin_fanout['Out'] == fo, 'Gate'].iloc[0]}-{fo}" for fo in row['Fanout'] if not df_fanin_fanout.loc[df_fanin_fanout['Out'] == fo].empty])
            df_fanin_fanout.at[i, 'Fanout'] = fanout_str

    # Processing Fanin similar to Fanout
    for i, row in df_fanin_fanout.iterrows():
        fanin_str = ','.join([f"INPUT-{fi}" if fi in inputs else f"{df_fanin_fanout.loc[df_fanin_fanout['Out'] == fi, 'Gate'].iloc[0]}-{fi}" for fi in row['Fanin'] if (fi in inputs or not df_fanin_fanout.loc[df_fanin_fanout['Out'] == fi].empty)])
        df_fanin_fanout.at[i, 'Fanin'] = fanin_str


    # fanouts printed to txt file 
    with open("ckt_details.txt", "a") as txt:  # Open in append mode
        txt.write("Fanout...\n")
        for i in range((df_fanin_fanout.shape[0])):
            txt.write(df_fanin_fanout['Gate'][i])
            txt.write("-")
            txt.write(df_fanin_fanout['Out'][i])
            txt.write(":")
            txt.write(df_fanin_fanout['Fanout'][i])
            txt.write("\n")
    #fanins printed to txt file 
        txt.write("Fanin...\n")
        for i in range((df_fanin_fanout.shape[0])):
            txt.write(df_fanin_fanout['Gate'][i])
            txt.write("-")
            txt.write(df_fanin_fanout['Out'][i])
            txt.write(":")
            txt.write(df_fanin_fanout['Fanin'][i])
            txt.write("\n")
        sys.exit(0)

elif type and args.read_nldm:
    

# Initializing  lists to store  data
    cells = []
    capacitance = []
    index1_delay_lists = []  
    index1_slew_lists = []
    index2_delay_lists=[]
    index2_slew_lists=[]
    values_delay=[]
    values_slew=[] 
    cell_delays=[]
    output_slews=[]
    def extract_cell_delay(line):
        # checking lines starting with cell delay 
        matches = re.search(r'cell_delay\(Timing_(\d+)_(\d+)\)', line)
        if matches:
            # finding the size of matrix in cell delay , for future : not used in code .. in this assumes a matrix of 7*7
            return [int(matches.group(1)), int(matches.group(2))]
        return None
    def extract_slew_delay(line):
        # similarly output slew searching 
        matches = re.search(r'output_slew\(Timing_(\d+)_(\d+)\)', line)
        if matches:
            # not used 
            return [int(matches.group(1)), int(matches.group(2))]
        return None
    def process_index_values(index_string):
        # removing all "" and , from each line 
        index_values = index_string.strip('"').split(',')
        # most values decimal so converting value 
        return [float(value) for value in index_values]

    def print_cell_contents(file_path):
        val_flag=0
        val_count=0
        cell_start_pattern = re.compile(r'cell\s*\((.*?)\)')  
        capacitance_pattern = re.compile(r'capacitance\s*:\s*(\d+\.\d+);')
        index_pattern = re.compile(r'index_1\s*\("(.*?)"\);')
        index_pattern2 = re.compile(r'index_2\s*\("(.*?)"\);')  
        values= re.compile(r'values\s*\("(.*?)"\);')
        cell_delay_pattern =  re.compile(r'cell_delay\(Timing_(\d+)_(\d+)\)')            #not used assumed values to be 7*7
        output_slew_pattern = re.compile(r'output_slew\(Timing_(\d+)_(\d+)\)')          #not used assumed values to be 7*7

        quotes=re.compile(r'"(.*?)"')  # for values 

        with open(file_path, 'r') as file:
            inside_delay=False      # check if loop is inside delay ;
            iterator = iter(file)

            inside_cell = False
            cnt=0  # flag for checking inside delay loop or outside 

            for line in file:
                cell_delay = extract_cell_delay(line)  
                if cell_delay is not None:
                    cell_delays.append(cell_delay)         #cell delays added to list
                    continue
                output_slew = extract_slew_delay(line)
                if output_slew is not None:
                    output_slews.append(output_slew)                #slews added to list 
                    continue
                if cell_start_pattern.search(line):
                    inside_cell = True
                    cell_name = cell_start_pattern.search(line).group(1)    #cells checked 
                    cells.append(cell_name)

                elif inside_cell and capacitance_pattern.search(line):
                    cap_value = float(capacitance_pattern.search(line).group(1)) #capacitance added to list 
                    capacitance.append(cap_value)

                elif inside_cell and index_pattern.search(line):
                    index_values = process_index_values(index_pattern.search(line).group(1))
                    if cnt%2 ==0:
                        index1_delay_lists.append(index_values)
                        
                        cnt+=1
                    else:
                        index1_slew_lists.append(index_values)
                        cnt+=1
                elif inside_cell and index_pattern2.search(line):
                    index_values=process_index_values(index_pattern2.search(line).group(1))
                    if cnt%2 ==0:
                        index2_delay_lists.append(index_values)
                        inside_delay=True
                    else:
                        index2_slew_lists.append(index_values)
                        inside_delay=False
                elif  inside_cell and values.search(line):
                    index_values=process_index_values(values.search(line).group(1))
                    if  val_flag%2==0:                              #second flag used to toggle value line between delay and slew 
                            values_delay.append(index_values)
                            val_flag+=1
                            
                    else:
                            values_slew.append(index_values)
                

                elif  inside_cell and values.search(line):       
                    index_values=process_index_values(values.search(line).group(1)) #similar line as above to avoid zero error
                    if  val_count==0:
                            values_delay.append(index_values)
                            val_count+=1
                    else:
                            values_slew.append(index_values)

                elif inside_cell and quotes.search(line): # checking for "" to add to values 
                    if val_count<7:
                        index_values=process_index_values(quotes.search(line).group(1))
                        values_delay.append(index_values)
                        val_count+=1
                    else :
                        index_values=process_index_values(quotes.search(line).group(1))
                        values_slew.append(index_values)
                        val_count+=1
                        if val_count==14:
                            val_count=0
                


                elif inside_cell and '}' in line:
                    if '}' in file.readline():  # two } in adjacent line marks end of a cell description 
                        inside_cell = False

    # Path to  file used for lib file . since single .lib file is used  
    file_path = 'sample_NLDM.lib'
    print_cell_contents(file_path)

    # Convert lists of lists into DataFrames
    index1_delay_df = pd.DataFrame(index1_delay_lists, columns=[f'Delay_{i}' for i in range(len(index1_delay_lists[0]))])  #each of the lists are added to dataframe 
    index1_slew_df = pd.DataFrame(index1_slew_lists, columns=[f'Slew_{i}' for i in range(len(index1_slew_lists[0]))])
    index2_delay_df = pd.DataFrame(index2_delay_lists, columns=[f'Delay_{i}' for i in range(len(index2_delay_lists[0]))])
    index2_slew_df = pd.DataFrame(index2_slew_lists, columns=[f'Slew_{i}' for i in range(len(index2_slew_lists[0]))])

    print("Cells:", cells)                 #print statements just for verification . can be removed 
    print("Capacitance:", capacitance)
    print("Index 1 Delay DataFrame:\n", index1_delay_df)
    print("Index 1 Slew DataFrame:\n", index1_slew_df)
    print("index 2 delay ",index2_delay_df)
    print("index 2 slew ",index2_slew_df)
    print("Output Slews Array:", output_slews)
    print("Cell Delays Array:", cell_delays)

    def print_txt(type):
        with open('delay_LUT.txt', 'w+') as fi:                     # text for delay generated 
            if type == 'delays':
                for i, cell in enumerate(cells):
                    fi.write("\n")
                    fi.write(f"cell: {cell}\n")
                    
                    # string for adding to dataframe  
                    input_slews_str = ' '.join(map(str, index1_delay_df.iloc[i].values))
                    fi.write(f"input slews:{input_slews_str}\n")
                    load_str=' '.join(map(str,index2_delay_df.iloc[i].values))
                    fi.write(f"load cap: {load_str}\n\n")
                    fi.write("delays:\n")
                    for j in range(i * 7, (i + 1) * 7):
                        row = values_delay[j]
                        fi.write(' '.join(map(str, row)) + '\n')
            if type=='slews':
                for i, cell in enumerate(cells):
                    fi.write("\n")
                    fi.write(f"cell: {cell}\n")
                    
                    # adding the row together in a string 
                    input_slews_str = ' '.join(map(str, index1_slew_df.iloc[i].values))
                    fi.write(f"input slews:{input_slews_str}\n")
                    load_str=' '.join(map(str,index2_slew_df.iloc[i].values))
                    fi.write(f"load cap: {load_str}\n\n")
                    fi.write("slews:\n")
                    for j in range(i * 7, (i + 1) * 7):
                        row = values_slew[j]
                        fi.write(' '.join(map(str, row)) + '\n')
    print_txt(type)


