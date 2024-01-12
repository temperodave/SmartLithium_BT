class Smart_Lithium:
  def __init__(self, Mac_address):
    self.Mac_address=Mac_address
    self.BMS_Flags = ''
    self.Error_Flags = ''
    self.Cell_V = []
    self.Temp = 0
    self.Voltage = 0
    self.Balancer_Status = 0

  def parse_hex(self,hex_str):
    self.BMS_Flags = hex_str[0:8]
    self.Error_Flags = hex_str[8:12]
    self.Temp = (int(hex_str[30:32],16) & 0x7f)- 40
    self.Voltage = (int(hex_str[28:30]+hex_str[26:28],16) & 0x0FFF) / 100
    self.Balancer_Status = hex_str[29:30]
    cell_voltages=int(hex_str[24:26]+hex_str[22:24]+hex_str[20:22]+hex_str[18:20]+hex_str[16:18]+hex_str[14:16]+hex_str[12:14],16)
    for i in range(8):
        self.Cell_V.insert(i,round((cell_voltages >>(7*i) & 0x000000000000007F) /100 + 2.6 , 2))
        
  def __str__(self):
    return f"BMS_Flags: {self.BMS_Flags} Error_Flags: {self.Error_Flags} Temp:{self.Temp} Voltage: {self.Voltage} Balancer_Status:{self.Balancer_Status} Cell_Voltages:{self.Cell_V}"


class BatteryMonitor:
  def __init__(self, Name):
    self.Name = Name
    self.remaining_mins = 0
    self.voltage = 0
    self.alarm = 0
    self.current = 0
    self.aux_value = 0
    self.aux_mode = 0
    self.consumed_ah = 0
    self.soc = 0

  def parse_hex(self,hex_str):
    self.remaining_mins = int(hex_str[2:4]+hex_str[0:2],16)
    self.voltage = int(hex_str[6:8]+hex_str[4:6],16)/100
    self.alarm = int(hex_str[10:12]+hex_str[8:10],16)
    self.aux_value = int(hex_str[14:16]+hex_str[12:14],16)
    self.current = int(hex_str[20:22]+hex_str[18:20]+hex_str[16:18],16)
    self.consumed_ah = int(hex_str[24:26]+hex_str[22:24],16)
    self.soc = ((int(hex_str[28:30]+hex_str[26:28],16) & 0x3FF0) >> 4) / 10
#    print('SOC: ',(hex_str[28:30]+hex_str[26:28]) >> 4)

  def __str__(self):
    return f"Remaining_Mins: {self.remaining_mins} Voltage: {self.voltage} alarm:{self.alarm} current: {self.current} Consumed_AH:{self.consumed_ah} SOC:{self.soc}"
    

