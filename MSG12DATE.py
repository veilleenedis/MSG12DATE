import serial
import re
import time

def calculate_checksum(data_string):
    checksum = sum(ord(char) for char in data_string) & 0x3F
    checksum += 0x20
    return chr(checksum)

def setup_serial(port, baud_rate):
    return serial.Serial(port, baud_rate, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, bytesize=serial.SEVENBITS, timeout=2)

def detect_baud_rate(ser):
    for baud_rate in [1200, 9600]:
        ser.baudrate = baud_rate
        ser.reset_input_buffer()
        time.sleep(2)
        data = ser.read(1500)
        if ('PAPP' in data.decode('ascii', errors='ignore') and baud_rate == 1200) or \
           ('SINSTS' in data.decode('ascii', errors='ignore') and baud_rate == 9600):
            return baud_rate
    return None

ser_read = setup_serial('COM7', 1200)
ser_write = setup_serial('COM4', 1200)
test = 0
while True:
    current_baud_rate = detect_baud_rate(ser_read)
    if current_baud_rate:   
        ser_read.baudrate = current_baud_rate
        ser_write.baudrate = current_baud_rate
        print(f"Baud rate détecté: {current_baud_rate}")
        try:
            while True:
                data = ser_read.readline().decode('ascii', errors='ignore').strip()
                if data:
                    print(f"Data read: {data}")
                    if 'PAPP' in data:
                        match = re.search(r'PAPP\s+(\d+)', data)
                        if match:
                            value = int(match.group(1)) + 500
                            data_without_checksum = re.sub(r'PAPP\s+\d+', f'PAPP {value}', data[:-2])
                            checksum = calculate_checksum(data_without_checksum)
                            new_data = data_without_checksum + ' ' + checksum
                    elif 'MSG1' in data and current_baud_rate == 9600:
                        match = re.search(r'MSG1\s+([HhEe]\d+(\s+)?)', data)
                        if match:
                            test = 1
                            value_MSG1 = match.group(1)
                        else:
                            test = 0    
                    elif 'DATE' in data and current_baud_rate == 9600:
                        match = re.search(r'DATE\t([HhEe]\d+\t\t)', data)
                        if match:
                            if test==1:
                                data_without_checksum = re.sub(r'DATE\t([HhEe]\d+)\t\t', f'DATE\t{value_MSG1}\t\t', data[:-1]) # Removing last char assuming it's checksum
                                checksum = calculate_checksum(data_without_checksum)
                                new_data = data_without_checksum  + checksum # Adding HT as separator
                    else:
                        new_data = data
                    if 'ADSC' in new_data:
                        ser_write.write(b'\x02' + b'\n' + new_data.encode('ascii') + b'\r')
                    elif 'PJOURF+1' in new_data:
                        ser_write.write(b'\n' + new_data.encode('ascii') + b'\r' + b'\x03')
                    else:        
                        ser_write.write(b'\n' + new_data.encode('ascii') + b'\r')
                    
                    print(f"Data written: {new_data}")
                else:
                    print("Aucune donnée valide reçue, réessai de la détection du baud rate...")
                    current_baud_rate = detect_baud_rate(ser_read)
                    if current_baud_rate:
                        ser_read.baudrate = current_baud_rate
                        ser_write.baudrate = current_baud_rate
                    else:
                        print("Impossible de détecter le baud rate, vérifiez les connexions.")
                        break
        except serial.SerialException as e:
            print(f"Erreur de communication série : {e}")
        except KeyboardInterrupt:
            ser_read.close()
            ser_write.close()
            print("Arrêt du script par l'utilisateur.")
            break
    else:
        print("Impossible de détecter le baud rate, réessai...")
        time.sleep(2)