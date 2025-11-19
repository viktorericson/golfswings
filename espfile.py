# ESP32 Feather V2 I2C Scanner and Sensor Test
import time
import board
import busio
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

print("ESP32 Feather V2 I2C Scanner")
print("=" * 40)

# First, let's see what pins are available
print("Available board attributes:")
available_pins = [attr for attr in dir(board) if not attr.startswith('_')]
print(available_pins[:20])  # Show first 20 attributes
print("...")
print(f"Total attributes: {len(available_pins)}")

# Test only the pins we know exist
pin_combinations = [
    ("Default I2C", board.SCL, board.SDA),
    ("A5/A4", board.A5, board.A4),
    ("A1/A0", board.A1, board.A0),
]

working_buses = []

for name, scl_pin, sda_pin in pin_combinations:
    print(f"\nTesting {name} - SCL: {scl_pin}, SDA: {sda_pin}")
    try:
        i2c = busio.I2C(scl_pin, sda_pin)
        
        # Scan for devices
        while not i2c.try_lock():
            pass
        
        try:
            devices = i2c.scan()
            if devices:
                print(f"  ✅ Found {len(devices)} device(s): {[hex(addr) for addr in devices]}")
                working_buses.append((name, scl_pin, sda_pin, i2c, devices))
                
                # Check if our sensors are present
                if 0x53 in devices:
                    print(f"    🎯 ADXL375 found at 0x53!")
                if 0x6A in devices:
                    print(f"    🎯 LSM6DSOX found at 0x6A!")
            else:
                print(f"  ❌ No devices found")
        finally:
            i2c.unlock()
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    time.sleep(0.1)

print("\n" + "=" * 40)
if not working_buses:
    print("❌ No I2C devices found! Check your wiring:")
    print("  • Ensure VCC is connected to 3V (not 5V)")
    print("  • Ensure GND is connected to ground")
    print("  • Check SCL/SDA connections")
    print("  • Try adding 4.7kΩ pull-up resistors on SCL/SDA lines")
    exit()

print(f"✅ Found {len(working_buses)} working I2C bus(es)")

# Use the first working bus for our sensors
bus_name, scl_pin, sda_pin, i2c_bus, devices = working_buses[0]
print(f"Using {bus_name} for sensors")

# If we have multiple buses, try to assign sensors optimally
if len(working_buses) >= 2:
    # Try to separate sensors on different buses
    print("Multiple buses available - will use separate buses for each sensor")

print("\n🔍 I2C Scanner complete!")
print("📋 Summary of found devices:")
for name, scl, sda, i2c, devices in working_buses:
    print(f"  {name}: {[hex(addr) for addr in devices]}")
    
print("\n✅ Connect your sensors and re-run to confirm they're detected!")

# Check what we found
if 0x6A in working_buses[0][4]:  # LSM6DSOX found
    print("✅ LSM6DSOX is connected and detected!")
if 0x53 not in working_buses[0][4]:  # ADXL375 not found
    print("❌ ADXL375 not detected - check:")
    print("  • Is VIN connected to 3V?")
    print("  • Is GND connected to ground?") 
    print("  • Are SCL/SDA connected to the default I2C pins?")
    print("  • Try connecting both sensors to the same I2C bus (shared)")

# Perfect! Both sensors detected on shared I2C bus
if 0x53 in working_buses[0][4] and 0x6A in working_buses[0][4]:
    print("🎉 PERFECT! Both sensors detected on shared I2C bus!")
    print("✅ ADXL375 (0x53) + LSM6DSOX (0x6A) = Complete golf swing monitoring setup")
    print("\n🚀 Ready to run the main sensor code!")

# Clean up scanner I2C instances to free the pins
print("🔄 Cleaning up scanner I2C instances...")
for name, scl, sda, i2c, devices in working_buses:
    try:
        i2c.deinit()
        print(f"  ✅ Released {name} I2C bus")
    except:
        pass
        
# Clear the list to help garbage collection
working_buses.clear()
time.sleep(0.1)  # Brief pause to ensure cleanup

# Remove scanner exit and enable the main code
# import sys  
# sys.exit()

# Initialize BLE
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)
ble.name = "GOLFSWING_MONITOR"

# Set up I2C buses for sensors
# Option 1: Use shared I2C bus (both sensors on same bus) - RECOMMENDED
# Option 2: Use separate I2C buses (sensors on different GPIO pins)

# ADXL375 I2C address (default: 0x53, alternative: 0x1D if SDO connected to VCC)
ADXL375_ADDRESS = 0x53

# ADXL375 register addresses
ADXL375_REG_DEVID = 0x00        # Device ID register (should read 0xE5)
ADXL375_REG_POWER_CTL = 0x2D    # Power control register
ADXL375_REG_DATA_FORMAT = 0x31  # Data format register
ADXL375_REG_DATAX0 = 0x32       # X-axis data register (LSB)

# LSM6DSOX I2C address (default: 0x6A, alternative: 0x6B if SA0 connected to VCC)
LSM6DSOX_ADDRESS = 0x6A

# LSM6DSOX register addresses
LSM6DSOX_REG_WHO_AM_I = 0x0F      # Device ID register (should read 0x6C)
LSM6DSOX_REG_CTRL1_XL = 0x10      # Accelerometer control register 1
LSM6DSOX_REG_CTRL2_G = 0x11       # Gyroscope control register 2
LSM6DSOX_REG_OUTX_L_G = 0x22      # Gyroscope X-axis low byte
LSM6DSOX_REG_OUTX_L_A = 0x28      # Accelerometer X-axis low byte

# Initialize shared I2C bus
i2c_shared = None

def read_adxl375():
    """Read accelerometer data from ADXL375 via raw I2C communication"""
    if i2c_shared is None:
        return 0.0, 0.0, 0.0
    while not i2c_shared.try_lock():
        pass
    try:
        # Read 6 bytes starting from DATAX0 register (X, Y, Z axis data - 2 bytes each)
        result = bytearray(6)
        i2c_shared.writeto_then_readfrom(ADXL375_ADDRESS, bytes([ADXL375_REG_DATAX0]), result)
        
        # Convert bytes to signed 16-bit integers (little endian)
        x_raw = (result[1] << 8) | result[0]
        y_raw = (result[3] << 8) | result[2]
        z_raw = (result[5] << 8) | result[4]
        
        # Convert to signed integers (2's complement for 16-bit values)
        if x_raw > 32767:
            x_raw -= 65536
        if y_raw > 32767:
            y_raw -= 65536
        if z_raw > 32767:
            z_raw -= 65536
        
        # Convert raw values to acceleration in g-force
        # ADXL375 scale factor: 49mg/LSB = 0.049 g/LSB
        scale_factor = 0.049
        accel_x_g = x_raw * scale_factor
        accel_y_g = y_raw * scale_factor
        accel_z_g = z_raw * scale_factor
        
        # Convert from g-force to m/s² (multiply by 9.81)
        accel_x = accel_x_g * 9.81
        accel_y = accel_y_g * 9.81
        accel_z = accel_z_g * 9.81
        
        return accel_x, accel_y, accel_z
        
    finally:
        i2c_shared.unlock()

def read_lsm6dsox():
    """Read accelerometer and gyroscope data from LSM6DSOX via raw I2C communication"""
    if i2c_shared is None:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    while not i2c_shared.try_lock():
        pass
    try:
        # Read accelerometer data (6 bytes starting from OUTX_L_A)
        accel_result = bytearray(6)
        i2c_shared.writeto_then_readfrom(LSM6DSOX_ADDRESS, bytes([LSM6DSOX_REG_OUTX_L_A]), accel_result)
        
        # Read gyroscope data (6 bytes starting from OUTX_L_G)
        gyro_result = bytearray(6)
        i2c_shared.writeto_then_readfrom(LSM6DSOX_ADDRESS, bytes([LSM6DSOX_REG_OUTX_L_G]), gyro_result)
        
        # Convert accelerometer bytes to signed 16-bit integers (little endian)
        accel_x_raw = (accel_result[1] << 8) | accel_result[0]
        accel_y_raw = (accel_result[3] << 8) | accel_result[2]
        accel_z_raw = (accel_result[5] << 8) | accel_result[4]
        
        # Convert gyroscope bytes to signed 16-bit integers (little endian)
        gyro_x_raw = (gyro_result[1] << 8) | gyro_result[0]
        gyro_y_raw = (gyro_result[3] << 8) | gyro_result[2]
        gyro_z_raw = (gyro_result[5] << 8) | gyro_result[4]
        
        # Convert to signed integers (2's complement for 16-bit values)
        def to_signed_16bit(value):
            return value - 65536 if value > 32767 else value
        
        accel_x_raw = to_signed_16bit(accel_x_raw)
        accel_y_raw = to_signed_16bit(accel_y_raw)
        accel_z_raw = to_signed_16bit(accel_z_raw)
        
        gyro_x_raw = to_signed_16bit(gyro_x_raw)
        gyro_y_raw = to_signed_16bit(gyro_y_raw)
        gyro_z_raw = to_signed_16bit(gyro_z_raw)
        
        # Convert accelerometer to m/s² (±16g range, 16-bit resolution)
        # LSM6DSOX: 32768 LSB = ±16g, so 1 LSB = 16g/32768 = 0.000488 g
        accel_scale = 16.0 / 32768.0 * 9.81  # Convert to m/s²
        accel_x = accel_x_raw * accel_scale
        accel_y = accel_y_raw * accel_scale
        accel_z = accel_z_raw * accel_scale
        
        # Convert gyroscope to rad/s (±2000 dps range, 16-bit resolution)
        # LSM6DSOX: 32768 LSB = ±2000 dps, so 1 LSB = 2000/32768 = 0.061 dps
        # Convert dps to rad/s: multiply by π/180
        gyro_scale = 2000.0 / 32768.0 * 3.14159 / 180.0  # Convert to rad/s
        gyro_x = gyro_x_raw * gyro_scale
        gyro_y = gyro_y_raw * gyro_scale
        gyro_z = gyro_z_raw * gyro_scale
        
        return accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z
        
    finally:
        i2c_shared.unlock()

try:
    # USING SHARED I2C BUS - Both sensors on same bus (RECOMMENDED)
    i2c_shared = busio.I2C(board.SCL, board.SDA)
    print("🔄 Initializing shared I2C bus for both sensors...")
    
    # Initialize the ADXL375 sensor
    def init_adxl375():
        while not i2c_shared.try_lock():
            pass
        try:
            # Check device ID to verify sensor is connected
            device_id = bytearray(1)
            i2c_shared.writeto_then_readfrom(ADXL375_ADDRESS, bytes([ADXL375_REG_DEVID]), device_id)
            print(f"  ADXL375 device ID: 0x{device_id[0]:02X}")
            if device_id[0] != 0xE5:
                raise ValueError(f"ADXL375 not found! Got device ID: 0x{device_id[0]:02X}, expected 0xE5")
            
            # Configure power control: set measure bit (bit 3) to enable measurement mode
            i2c_shared.writeto(ADXL375_ADDRESS, bytes([ADXL375_REG_POWER_CTL, 0x08]))
            time.sleep(0.01)
            
            # Configure data format: Full resolution mode + ±200g range
            # Bit 3 = 1 (full resolution), Bits 1:0 = 11 (±200g range for ADXL375)
            i2c_shared.writeto(ADXL375_ADDRESS, bytes([ADXL375_REG_DATA_FORMAT, 0x0B]))
            time.sleep(0.01)
            
        finally:
            i2c_shared.unlock()
    
    # Initialize the LSM6DSOX sensor
    def init_lsm6dsox():
        while not i2c_shared.try_lock():
            pass
        try:
            # Check device ID to verify sensor is connected
            device_id = bytearray(1)
            i2c_shared.writeto_then_readfrom(LSM6DSOX_ADDRESS, bytes([LSM6DSOX_REG_WHO_AM_I]), device_id)
            print(f"  LSM6DSOX device ID: 0x{device_id[0]:02X}")
            if device_id[0] != 0x6C:
                raise ValueError(f"LSM6DSOX not found! Got device ID: 0x{device_id[0]:02X}, expected 0x6C")
            
            # Configure accelerometer: 208 Hz, ±16g range, high performance mode
            # CTRL1_XL: ODR=0101 (208Hz), FS=11 (±16g), LPF2_XL_EN=0
            i2c_shared.writeto(LSM6DSOX_ADDRESS, bytes([LSM6DSOX_REG_CTRL1_XL, 0x5C]))
            time.sleep(0.01)
            
            # Configure gyroscope: 208 Hz, ±2000 dps range, high performance mode
            # CTRL2_G: ODR=0101 (208Hz), FS=11 (±2000dps)
            i2c_shared.writeto(LSM6DSOX_ADDRESS, bytes([LSM6DSOX_REG_CTRL2_G, 0x5C]))
            time.sleep(0.01)
            
        finally:
            i2c_shared.unlock()
    
    # Initialize both sensors
    print("🔄 Initializing ADXL375...")
    try:
        init_adxl375()
        print("✅ ADXL375 initialized successfully!")
    except Exception as e:
        print(f"❌ ADXL375 initialization failed: {e}")
        raise
    
    print("🔄 Initializing LSM6DSOX...")
    try:
        init_lsm6dsox()
        print("✅ LSM6DSOX initialized successfully!")
    except Exception as e:
        print(f"❌ LSM6DSOX initialization failed: {e}")
        raise
    
    print(f"Found sensors configured for golf swings:")
    print(f"  ADXL375 - High-g accelerometer:")
    print(f"    Range: ±200g, Resolution: 49mg/LSB, Address: 0x{ADXL375_ADDRESS:02X}")
    print(f"  LSM6DSOX - IMU sensor:")
    print(f"    Accel range: ±16g, Gyro range: ±2000dps, Address: 0x{LSM6DSOX_ADDRESS:02X}")
    
    print("Starting Bluetooth advertising...")
    
    # Start advertising
    ble.start_advertising(advertisement)
    print("Waiting for Bluetooth connection...")
    
    while True:
        # Check if a device is connected
        if ble.connected:
            print("Bluetooth device connected!")
            
            # Main loop while connected - fast reading mode
            reading_count = 0
            while ble.connected:
                # Read high-g accelerometer data from ADXL375 (for impact detection)
                adxl_accel_x, adxl_accel_y, adxl_accel_z = read_adxl375()
                
                # Read IMU data from LSM6DSOX (for detailed motion analysis)
                lsm_accel_x, lsm_accel_y, lsm_accel_z, gyro_x, gyro_y, gyro_z = read_lsm6dsox()
                
                # Use LSM6DSOX accelerometer for normal readings, ADXL375 for high-impact detection
                # You can choose which accelerometer data to use based on your needs
                accel_x, accel_y, accel_z = lsm_accel_x, lsm_accel_y, lsm_accel_z
                
                # No temperature sensor available, set to room temperature
                temperature = 25.0
                
                # Compact binary-like format for fast phone parsing
                # Format: ax,ay,az,gx,gy,gz,hx,hy,hz,t
                # LSM accel (ax,ay,az), LSM gyro (gx,gy,gz), ADXL high-g (hx,hy,hz), temp (t)
                data = f'{accel_x:.3f},{accel_y:.3f},{accel_z:.3f},{gyro_x:.4f},{gyro_y:.4f},{gyro_z:.4f},{adxl_accel_x:.1f},{adxl_accel_y:.1f},{adxl_accel_z:.1f},{temperature:.0f}\n'
                
                # Send data via Bluetooth
                uart_service.write(data.encode('utf-8'))
                
                # Only print every 50th reading to avoid console spam (every 0.5 seconds at 100Hz)
                reading_count += 1
                if reading_count % 50 == 0:
                    print("Sent: Accel(%.2f, %.2f, %.2f) m/s², Gyro(%.2f, %.2f, %.2f) rad/s, Temp: %.1f°C (reading #%d @ 100Hz)" 
                          % (accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temperature, reading_count))
                
                # High-speed reading for golf swing capture - 100Hz (100 times per second)
                time.sleep(0.01)
            
            print("Bluetooth device disconnected. Restarting advertising...")
            ble.start_advertising(advertisement)
        else:
            # Not connected, just wait a bit
            time.sleep(0.1)

except ValueError as ve:
    print(f"Sensor initialization error: {ve}")
    print("Check wiring and run the I2C scanner.")
except Exception as e:
    print(f"General error: {e}")
    print(f"Error type: {type(e).__name__}")
    # If BLE fails, fall back to console output
    print("Falling back to console output only...")
    while True:
        try:
            # Read from both sensors
            adxl_accel_x, adxl_accel_y, adxl_accel_z = read_adxl375()
            lsm_accel_x, lsm_accel_y, lsm_accel_z, gyro_x, gyro_y, gyro_z = read_lsm6dsox()
            
            # Use LSM6DSOX data for main output
            accel_x, accel_y, accel_z = lsm_accel_x, lsm_accel_y, lsm_accel_z
            temperature = 25.0
            
            # Use same compact format as BLE for consistency
            data_line = f'{accel_x:.3f},{accel_y:.3f},{accel_z:.3f},{gyro_x:.4f},{gyro_y:.4f},{gyro_z:.4f},{adxl_accel_x:.1f},{adxl_accel_y:.1f},{adxl_accel_z:.1f},{temperature:.0f}'
            print(data_line)
            time.sleep(0.01)  # High-speed readings for fallback mode too - 100Hz
        except Exception as e:
            print(f"Sensor read error: {e}")
            break
