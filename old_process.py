import sys

idle_retract_dist = 30           # Distance to retract for idle
retract_speed= 25*60        # Speed to retract for idle (converted from mm/s to mm/min)
hop_height = 5              # Height to hop for tool change
fibre_length = 50           # Length of fibre between nozzle and cutting point
min_fibre_length = 70       # Minimum length of fibre to extrude
extrude_cancel_length = 1   # Length before end of fibre extrusion to cancel extrusion to prevent oozing
layer_skip = 2              # Number of layers between each fibre extrusion (set to 1 to extrude every layer)


# gcode_path = sys.argv[-1]
gcode_path = "C:\\Users\\dhilu\\Documents\\Anisoprint\\test.gcode"

with open(gcode_path, "r", encoding="utf-8", errors="ignore") as f:
    data = f.readlines()

# Find CCF extruder temp
ccfTemp = None
for line in reversed(data):
    if line.startswith("; temperature ="):
        ccfTemp = line.split(",")[1].replace("\n", "")
        break

# Find Z rapid speed for hops
z_rapid = None
for line in reversed(data):
    if line.startswith("; machine_max_feedrate_z ="):
        z_rapid = float(line.split("=")[1].replace("\n", "").strip())*60
        break

# Find travel speed
travel_speed = None
for line in reversed(data):
    if line.startswith("; travel_speed ="):
        travel_speed = float(line.split("=")[1].replace("\n", "").strip())*60
        break

# Find idle temp
idleTemp = [None, None]
for line in reversed(data):
    if line.startswith("; idle_temperature ="):
        idleTemp[0] = line.split(",")[0].split(" ")[-1]
        idleTemp[1] = line.split(",")[1].replace("\n", "")
        break

# Find retract distances
retract_dist = [None, None]
for line in reversed(data):
    if line.startswith("; retract_length ="):
        retract_dist[0] = float(line.split(",")[0].split(" ")[-1])
        retract_dist[1] = float(line.split(",")[1].replace("\n", ""))
        break

# Find retract restart extra
restart_dist = [None, None]
for line in reversed(data):
    if line.startswith("; retract_restart_extra ="):
        restart_dist[0] = float(line.split(",")[0].split(" ")[-1]) + idle_retract_dist
        restart_dist[1] = float(line.split(",")[1].replace("\n", "")) + idle_retract_dist
        break

# Perimeter reordering
i = 0
layer_num = 0
perimeter_end = 0
perimeter_count = 0
move_perimeter = False
ignore_travel = True
while i < len(data)-5:
    line = data[i]

    # New layer, reset perimeter flag
    if line.startswith(";LAYER_NUM:"):
        layer_num = int(line.split(":")[1].replace("\n", ""))
        perimeter_count = 0
        move_perimeter = False
    
    # First perimeter seen
    if line.startswith(";TYPE:External perimeter") and perimeter_count == 0:
        perimeter_count += 1
        i += 1
        continue
    
    
    if perimeter_count > 0:
        # End of first perimeter, keep track of position
        if line.startswith(";TYPE:") and not line.startswith(";TYPE:External perimeter") and perimeter_count == 1:
            perimeter_end = i-1
            perimeter_count += 1
        
        # End of subsequent perimeter, stop moving
        if data[i+2].startswith(";TYPE:") and not line.startswith(";TYPE:External perimeter") and perimeter_count > 1:
            move_perimeter = False
        
        # New perimeter found, move to previous location
        if data[i+5].startswith(";TYPE:External perimeter"):
            move_perimeter = True
            ignore_travel = True
            perimeter_count += 1
        
        if line.startswith(";TYPE:External perimeter") and ignore_travel:
            ignore_travel = False

        if move_perimeter:
            # Check if this is a travel move, if so don't move
            # if (" X" in line and " Y" in line) and not " E" in line and not " F" in line and not ignore_travel:
            #     pass
            # else:
            data.insert(perimeter_end, data.pop(i))
            perimeter_end += 1
    i += 1



fibrePerim = 0
cancelPerim = 0
z_height = 0
layer_num = 0
prev_x = None
prev_y = None
u_dist = 0
extrude_fibre = 0
fibre_line_num = 0
perimeter_count = 0
skip = False

# # Fibre processing
# for lineNum in range(len(data)):
#     line = data[lineNum]
#     if skip:
#         if line.startswith(";TYPE:Perimeter"):
#             skip = False
#         continue

#     # Find the current Z height
#     if line.startswith(";Z:"):
#         z_height = float(line.split(":")[1].replace("\n", ""))
    
#     # Find the layer number
#     if line.startswith(";LAYER_NUM:"):
#         layer_num = int(line.split(":")[1].replace("\n", ""))
#         perimeter_count = 0

#     # Check if this is an internal perimeter
#     if line.startswith(";TYPE:Perimeter") and perimeter_count == 0:
#         # Check if this layer should have fibre, otherwise set flag to cancel perimeter extrusion for this layer
#         if layer_num % layer_skip != 0:
#             cancelPerim = 1
#             continue
#         fibrePerim = 1
#         extrude_fibre = 1
#         perimeter_count += 1

#         # Change tool
#         gcode = f"M104 T1 S{ccfTemp}\n"
#         gcode += f"G1 E-{idle_retract_dist} F{retract_speed}\n"
#         gcode += f"G1 Z{z_height+hop_height} F{z_rapid}\n"
#         gcode += f"G1 F{travel_speed}\n"
#         gcode += f"T1\n"
#         gcode += f"G1 Z{z_height} F{z_rapid}\n"
#         gcode += "PRIME_FIBRE\n"
#         gcode += f"G1 E{restart_dist[1]} F{retract_speed}\n"
#         gcode += f"G1 F{travel_speed}\n"

#         data.insert(lineNum+1, gcode)

#         # Define variables for fibre extrusion
#         prev_x = None
#         prev_y = None
#         u_dist = 0
#         continue

#     # If this is a perimeter to be cancelled, remove extrusion commands until the end of the perimeter
#     if cancelPerim:
#         # Stop cancelling perimeter extrusion after the end of the perimeter is reached
#         if data[lineNum].startswith(";LAYER_CHANGE"):
#             cancelPerim = 0
#             continue
        
#         if line.startswith("G1") or line.startswith("M73"):
#             data[lineNum] = ""

#     # If this is a preimeter for fibre extrusion
#     if fibrePerim:
#         # Fibre perimeter is over, switch back to main extruder
#         if line.startswith(";LAYER_NUM"):
#             fibrePerim = 0
#             gcode =  f"M104 T1 S{idleTemp[1]}\n"
#             gcode += f"G1 E-{idle_retract_dist} F{retract_speed}\n"
#             gcode += f"G1 Z{z_height+hop_height} F{z_rapid}\n"
#             gcode += f"G1 F{travel_speed}\n"
#             gcode += f"T0\n"
#             gcode += f"G1 Z{z_height} F{z_rapid}\n"
#             gcode += f"G1 E{restart_dist[0]} F{retract_speed}\n"
#             gcode += f"G1 F{travel_speed}\n"
#             data.insert(lineNum+1, gcode)
        
#         # Fibre perimeter extrusion is done, start looking backwards to find cut position
#         if extrude_fibre and ((line.startswith("G1 E-") and not line.startswith(f"G1 E-{idle_retract_dist}")) or line.startswith(";TYPE:Perimeter")):
#             extrude_fibre = 0
#             cut_dist = u_dist - fibre_length
#             i = lineNum-1
#             cur_dist = u_dist

#             # Check if fibre length is greater than minimum length
#             if u_dist < min_fibre_length:
#                 # Remove fibre extrusion commands
#                 line = data[i]
#                 exit = False
#                 while exit == False:
#                     data[i] = line.split(" U")[0] + "\n"
#                     i -= 1
#                     line = data[i]
#                     # if line.startswith("G1") and " E" in line and not (" U" in line):
#                     if line.startswith('PRIME_FIBRE'):
#                         data[i] = ""
#                         exit = True
#                 continue

#             # Iterate backwards from current point until fibre cut length is reached, removing fibre extrusion from the G1 commands as we go
#             while cur_dist > cut_dist:
#                 # Remove the current U parameter
#                 data[i] = data[i].split(" U")[0] + "\n"
#                 i -= 1
#                 if data[i].startswith("G1") and (" U" in data[i]):
#                     cur_dist = float(data[i].split(" U")[-1].replace("\n", ""))
#             data.insert(i+1, "CUT\n")

#             # Iterate backwards from current point until E cancel length is reached, removing E parameters from the G1 commands as we go to prevent oozing during idle
#             i = lineNum
#             cur_dist = 0
#             while cur_dist < extrude_cancel_length:
#                 if "U" in data[i]:  # Can't cancel extrusion if there is still fibre movement
#                     break

#                 if data[i].startswith("G1") and (" E" in data[i]):
#                     gcode = data[i].split(" E")[0] + "\n"
#                     cur_dist += float(data[i].split(" E")[1].replace("\n", ""))
#                     data[i] = gcode
#                 i -= 1

#         # Calculate fibre extrusion lengths and convert to absolute U axis position
#         if extrude_fibre and line.startswith("G1") and (" X" in line or " Y" in line):
#             # Increase extrusion amount to fully fill channel
#             if " E" in line:
#                 command, e_dist = line.split(" E")
#                 e_dist = float(e_dist.replace("\n", ""))
#                 line = command + " E" + str(e_dist * layer_skip) + "\n"

#             x = float(line.split(" X")[1].split(" ")[0])
#             y = float(line.split(" Y")[1].split(" ")[0])

#             if prev_x is None:
#                 prev_x = x
#                 prev_y = y
#                 continue
            
#             dist = ((x - prev_x)**2 + (y - prev_y)**2)**0.5
#             u_dist += dist
#             gcode = line.replace("\n", "") + f" U{round(u_dist, 3)}\n"

#             data[lineNum] = gcode
        
#             prev_x = x
#             prev_y = y
        
#         # Start a fibre extrude again if nozzle gets re-primed
#         if not extrude_fibre and (line.startswith(f"G1 E{int(retract_dist[0])}") or line.startswith(";TYPE:Perimeter")):
#             extrude_fibre = 1
#             prev_x = None
#             prev_y = None
#             u_dist = 0

#             data.insert(lineNum+1, "PRIME_FIBRE\n")
#             if line.startswith(";TYPE:Perimeter"):
#                 skip = True


with open(gcode_path, "w", encoding="utf-8", errors="ignore") as f:
    f.writelines(data)