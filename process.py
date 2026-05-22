import sys
idle_retract_dist = [30,30]
fibre_length = 50           # Length of fibre between nozzle and cutting point
min_fibre_length = 120       # Minimum length of fibre to extrude

T0_gcode =  """
T0\n
"""

T1_gcode =  """
T1\n
"""



# gcode_path = sys.argv[-1]
gcode_path = "C:\\Users\\dhilu\\Documents\\Anisoprint\\test.gcode"

with open("C:\\Users\\dhilu\\Documents\\Anisoprint\\template.gcode", "r", encoding="utf-8", errors="ignore") as f:
    data = f.readlines()

# Find Settings
ccfTemp = None
z_rapid = None
travel_speed = None
idleTemp = [None, None]
retract_dist = [None, None]
restart_dist = [None, None]

for line in reversed(data):
    match line:
        case line if line.startswith("; temperature ="):                # Find CCF extruder temp
            ccfTemp = line.split(",")[1].replace("\n", "")
        case line if line.startswith("; machine_max_feedrate_z ="):     # Find Z rapid speed
            z_rapid = float(line.split("=")[1].replace("\n", "").strip())*60
        case line if line.startswith("; travel_speed ="):               # Find travel speed
            travel_speed = float(line.split("=")[1].replace("\n", "").strip())*60
        case line if line.startswith("; idle_temperature ="):           # Find idle temps
            idleTemp[0] = line.split(",")[0].split(" ")[-1]
            idleTemp[1] = line.split(",")[1].replace("\n", "")
        case line if line.startswith("; retract_length ="):              # Find retract distances
            retract_dist[0] = int(line.split(",")[0].split(" ")[-1])
            retract_dist[1] = int(line.split(",")[1].replace("\n", ""))
        case line if line.startswith("; retract_restart_extra ="):        # Find restart distances
            restart_dist[0] = int(line.split(",")[0].split(" ")[-1])
            restart_dist[1] = int(line.split(",")[1].replace("\n", ""))
    
    if line.startswith("; prusaslicer_config = begin"):    # End of settings, stop searching
        break

# Move Perimeters
i = 0
layer_num = 0
perimeter_count = 0
perimeter_end = 0
move_perimeter = False
while i < len(data)-5:
    line = data[i]

    # New layer, reset perimeter flag
    if line.startswith(";LAYER_NUM:"):
        layer_num = int(line.split(":")[1].replace("\n", ""))
        perimeter_count = 0
        move_perimeter = False
    
    # First perimeter seen
    if line.startswith(";TYPE:External perimeter"):
        perimeter_count += 1

    # End of first perimeter, keep track of this position to move subsequent perimeter moves here
    if perimeter_count == 1 and line.startswith(";TYPE:") and not line.startswith(";TYPE:External perimeter"):
        perimeter_end = i-1
        # data.insert(perimeter_end, ";thingy go here\n")
        # i += 1                                                  # Increment by one to account for data insert
    
    if perimeter_count > 0:                                     # Perimeter count is incremented after this check, so this is true for subsequent perimeters
        # Find subsequent perimeters and change to perimeter move state
        if data[i+5].startswith(";TYPE:External perimeter"):
            move_perimeter = True

            # data.insert(i, ";thingy come from here\n")
            # i += 1                                              # Increment by one to account for data insert
        
        if move_perimeter:
            # End perimeter move state
            # CASE 1: Hop before next printer move
            if line.startswith(f"G1 E-{retract_dist[0]}") and not data[i+5].startswith(";TYPE:External perimeter"):    # Check that this isn't the start of an external perimeter
                move_perimeter = False
                # data.insert(i, ";thingy end here\n")
                # i += 1                                          # Increment by one to account for data insert
                continue
            
            # CASE 2: No hop
            if data[i+1].startswith(";TYPE:") and not data[i+1].startswith(";TYPE:External perimeter"):
                move_perimeter = False
                # data.insert(i, ";thingy end here\n")
                # i += 1                                          # Increment by one to account for data insert
                continue

            # Move perimeter move to end of first perimeter
            data.insert(perimeter_end, data.pop(i))
            perimeter_end += 1
    i += 1

i = 0
current_tool = 0

while i < len(data):
    line = data[i]

    # Logic if printing with T0
    if current_tool == 0:
        # Change to T1 on first perimeter seen
        if line.startswith(";TYPE:Perimeter"):
            data.insert(i, T1_gcode)
            current_tool = 1
            i += 1                                              # Increment by one to account for data insert
    
    # Logic if printing with T1
    if current_tool == 1:
        # Change back to T0 after finishing perimeters
        if line.startswith(";TYPE:") and not line.startswith(";TYPE:Perimeter"):
            data.insert(i, T0_gcode)
            current_tool = 0
            i += 1                                              # Increment by one to account for data insert
        
        # if we find a new perimeter section
        if line.startswith(";TYPE:Perimeter"):
            # Measure the length of this perimeter section
            j = i+1
            perimeter_length = 0
            prev_x = None
            prev_y = None
            while not (data[j].startswith(";TYPE:") or data[j].startswith(";LAYER_CHANGE")):    # Iterate until a new print section is found
                if data[j].startswith("G1") and ("X" in data[j] or "Y" in data[j]) and "E" in data[j]: # Check that this is a movement command
                    # Grab the X and Y coordinates of this movement command
                    x = float(data[j].split(" X")[1].split(" ")[0])
                    y = float(data[j].split(" Y")[1].split(" ")[0])

                    # Check if there is a previous coordinate
                    if prev_x is None:
                        prev_x = x
                        prev_y = y
                        j += 1
                        continue

                    distance = ((x-prev_x)**2 + (y-prev_y)**2)**0.5
                    perimeter_length += distance

                    prev_x = x
                    prev_y = y
                j += 1
            # If perimeter length is above threshold, we can extrude fibre, otherwise skip
            if perimeter_length < min_fibre_length:
                i += 1
                continue

            # Calculate distance at which to cut fibre
            cut_dist = perimeter_length - fibre_length

            # Start adding fibre commands to gcode

            # Add a fibre prime command
            data.insert(i, "PRIME_FIBRE\n")
            i += 1                                              # Increment by one to account for data insert

            j = i+1
            current_dist = 0
            prev_x = None
            prev_y = None
            while not (data[j].startswith(";TYPE:") or data[j].startswith(";LAYER_CHANGE")):    # Iterate until a new print section is found
                if data[j].startswith("G1") and ("X" in data[j] or "Y" in data[j]) and "E" in data[j]: # Check that this is a movement command
                    # Grab the X and Y coordinates of this movement command
                    x = float(data[j].split(" X")[1].split(" ")[0])
                    y = float(data[j].split(" Y")[1].split(" ")[0])

                    # Check if there is a previous coordinate
                    if prev_x is None:
                        prev_x = x
                        prev_y = y
                        j += 1
                        continue

                    distance = ((x-prev_x)**2 + (y-prev_y)**2)**0.5
                    current_dist += distance

                    if current_dist >= cut_dist:    # Adding this move would extrude too much fibre, cut before
                        # Add interpolated move to get a more accurate cut point
                        e = float(data[j].split(" E")[1].split("\n")[0])

                        ratio = (cut_dist - (current_dist - distance)) / distance
                        cut_x = round(prev_x + ratio * (x - prev_x), 3)
                        cut_y = round(prev_y + ratio * (y - prev_y), 3)
                        cut_e = round(e * ratio, 5)
                        rest_e = round(e - cut_e, 5)
                        cut_u = round(cut_dist, 5)
                        
                        data.insert(j, "CUT\n")
                        data.insert(j, f"G1 X{cut_x} Y{cut_y} E{cut_e} U{cut_u}\n")

                        # Adjust final move to correct for E value
                        data[j+2] = data[j+2].replace(f" E{e}", f" E{rest_e}")
                        break

                    # Add U move to extrude fibre
                    data[j] = data[j].replace("\n", f" U{round(current_dist, 5)}\n")

                    prev_x = x
                    prev_y = y
                j += 1
            

    
    i += 1



with open(gcode_path, "w", encoding="utf-8", errors="ignore") as f:
    f.writelines(data)