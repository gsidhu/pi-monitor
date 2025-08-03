import asyncio
import psutil
import time
import os
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for caching
_stats_cache = {}
_cache_timestamp = 0
_cache_duration = 0.5  # Cache for 500ms to avoid excessive system calls

templates = Jinja2Templates(directory="templates")

class SystemMonitor:
    def __init__(self):
        self.boot_time = psutil.boot_time()
        
    async def get_uptime(self) -> str:
        """Get system uptime in human readable format."""
        try:
            uptime_seconds = time.time() - self.boot_time
            minutes, seconds = divmod(int(uptime_seconds), 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            return f"{days}d {hours}h {minutes}m"
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return "Unknown"

    async def get_gpu_freq(self) -> int:
        """Get GPU frequency using vcgencmd."""
        try:
            process = await asyncio.create_subprocess_exec(
                "vcgencmd", "measure_clock", "core",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                return int(output.split("=")[-1]) // 1000000  # Convert Hz to MHz
            else:
                logger.warning(f"vcgencmd failed: {stderr.decode()}")
                return 0
        except Exception as e:
            logger.error(f"Error getting GPU frequency: {e}")
            return 0

    async def get_disk_io_rate(self) -> Tuple[float, float]:
        """Get disk I/O rates in MB/s."""
        try:
            # Get initial reading
            disk_io_1 = psutil.disk_io_counters()
            if disk_io_1 is None:
                return 0.0, 0.0
                
            # Wait for a short interval
            await asyncio.sleep(0.1)  # Shorter interval to reduce blocking
            
            # Get second reading
            disk_io_2 = psutil.disk_io_counters()
            if disk_io_2 is None:
                return 0.0, 0.0
                
            # Calculate rates per second
            time_diff = 0.1
            read_mb_s = (disk_io_2.read_bytes - disk_io_1.read_bytes) / (1024 * 1024) / time_diff
            write_mb_s = (disk_io_2.write_bytes - disk_io_1.write_bytes) / (1024 * 1024) / time_diff
            
            return max(0, read_mb_s), max(0, write_mb_s)
        except Exception as e:
            logger.error(f"Error getting disk I/O: {e}")
            return 0.0, 0.0

    async def get_network_io_rate(self) -> Tuple[float, float]:
        """Get network I/O rates in MB/s."""
        try:
            # Get initial reading
            net_io_1 = psutil.net_io_counters()
            if net_io_1 is None:
                return 0.0, 0.0
                
            # Wait for a short interval
            await asyncio.sleep(0.1)  # Shorter interval to reduce blocking
            
            # Get second reading
            net_io_2 = psutil.net_io_counters()
            if net_io_2 is None:
                return 0.0, 0.0
                
            # Calculate rates per second
            time_diff = 0.1
            recv_mb_s = (net_io_2.bytes_recv - net_io_1.bytes_recv) / (1024 * 1024) / time_diff
            sent_mb_s = (net_io_2.bytes_sent - net_io_1.bytes_sent) / (1024 * 1024) / time_diff
            
            return max(0, recv_mb_s), max(0, sent_mb_s)
        except Exception as e:
            logger.error(f"Error getting network I/O: {e}")
            return 0.0, 0.0

    async def get_fan_rpm(self) -> int:
        """Get fan RPM from hwmon."""
        try:
            hwmon_base = "/sys/class/hwmon"
            if not os.path.exists(hwmon_base):
                return 0
                
            for entry in os.listdir(hwmon_base):
                name_path = os.path.join(hwmon_base, entry, "name")
                if os.path.isfile(name_path):
                    try:
                        with open(name_path, "r") as f:
                            if f.read().strip() == "pwmfan":
                                fan_path = os.path.join(hwmon_base, entry, "fan1_input")
                                if os.path.isfile(fan_path):
                                    with open(fan_path, "r") as fan_file:
                                        return int(fan_file.read().strip())
                    except (ValueError, OSError) as e:
                        logger.warning(f"Error reading fan data from {entry}: {e}")
                        continue
            return 0
        except Exception as e:
            logger.error(f"Error getting fan RPM: {e}")
            return 0

    async def get_stats(self) -> Dict:
        """Get comprehensive system statistics."""
        global _stats_cache, _cache_timestamp
        
        # Check cache
        current_time = time.time()
        if current_time - _cache_timestamp < _cache_duration and _stats_cache:
            return _stats_cache
            
        try:
            # Get basic stats (these are fast)
            cpu_percent = psutil.cpu_percent(interval=None) / 100
            memory = psutil.virtual_memory()
            disk_usage = psutil.disk_usage("/")
            
            # Get CPU frequency
            cpu_freq = 0
            try:
                freq_info = psutil.cpu_freq()
                if freq_info:
                    cpu_freq = freq_info.current
            except Exception as e:
                logger.warning(f"Could not get CPU frequency: {e}")
            
            # Get temperature
            temp = 0
            try:
                temps = psutil.sensors_temperatures()
                if "cpu_thermal" in temps and temps["cpu_thermal"]:
                    temp = temps["cpu_thermal"][0].current
            except Exception as e:
                logger.warning(f"Could not get temperature: {e}")
            
            # Get load average
            load_avg = "0.00, 0.00, 0.00"
            try:
                loads = os.getloadavg()
                load_avg = ", ".join([f"{x:.2f}" for x in loads])
            except Exception as e:
                logger.warning(f"Could not get load average: {e}")
            
            # Get async stats concurrently
            uptime_task = asyncio.create_task(self.get_uptime())
            fan_task = asyncio.create_task(self.get_fan_rpm())
            gpu_freq_task = asyncio.create_task(self.get_gpu_freq())
            disk_io_task = asyncio.create_task(self.get_disk_io_rate())
            net_io_task = asyncio.create_task(self.get_network_io_rate())
            
            # Wait for all async operations
            uptime, fan_rpm, gpu_freq, (disk_read, disk_write), (net_recv, net_sent) = await asyncio.gather(
                uptime_task, fan_task, gpu_freq_task, disk_io_task, net_io_task,
                return_exceptions=True
            )
            
            # Handle exceptions in results
            if isinstance(uptime, Exception):
                uptime = "Unknown"
                logger.error(f"Uptime task failed: {uptime}")
            if isinstance(fan_rpm, Exception):
                fan_rpm = 0
                logger.error(f"Fan RPM task failed: {fan_rpm}")
            if isinstance(gpu_freq, Exception):
                gpu_freq = 0
                logger.error(f"GPU freq task failed: {gpu_freq}")
            if isinstance((disk_read, disk_write), Exception):
                disk_read, disk_write = 0.0, 0.0
                logger.error(f"Disk I/O task failed")
            if isinstance((net_recv, net_sent), Exception):
                net_recv, net_sent = 0.0, 0.0
                logger.error(f"Network I/O task failed")
            
            stats = {
                "cpu": round(cpu_percent, 3),
                "memory_percent": round(memory.percent / 100, 3),
                "temp": round(temp, 1),
                "uptime_human": uptime,
                "load_avg": load_avg,
                "fan_rpm": fan_rpm,
                "cpu_freq": round(cpu_freq, 1),
                "disk_usage_percent": round(disk_usage.percent / 100, 3),
                "gpu_freq": gpu_freq,
                "disk_read_mb_s": round(disk_read, 3),
                "disk_write_mb_s": round(disk_write, 3),
                "net_recv_mb_s": round(net_recv, 3),
                "net_sent_mb_s": round(net_sent, 3)
            }
            
            # Update cache
            _stats_cache = stats
            _cache_timestamp = current_time
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                "cpu": 0, "memory_percent": 0, "temp": 0, "uptime_human": "Unknown",
                "load_avg": "0.00, 0.00, 0.00", "fan_rpm": 0, "cpu_freq": 0,
                "disk_usage_percent": 0, "gpu_freq": 0, "disk_read_mb_s": 0,
                "disk_write_mb_s": 0, "net_recv_mb_s": 0, "net_sent_mb_s": 0
            }

class PowerMonitor:
    def __init__(self):
        self.rails = [
            ("3V7_WL_SW", 0, 8),
            ("3V3_SYS", 1, 9),
            ("1V8_SYS", 2, 10),
            ("DDR_VDD2", 3, 11),
            ("DDR_VDDQ", 4, 12),
            ("1V1_SYS", 5, 13),
            ("0V8_SW", 6, 14),
            ("VDD_CORE", 7, 15),
            ("0V8_AON", 16, 19),
            ("3V3_DAC", 17, 20),
            ("3V3_ADC", 18, 21),
            ("HDMI", 22, 23)
        ]

    async def read_pmic_channel(self, channel: int, unit: str) -> Optional[float]:
        """Read PMIC channel value asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                "vcgencmd", "pmic_read_adc", f"CH{channel}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"vcgencmd failed for CH{channel}: {stderr.decode()}")
                return None
                
            output = stdout.decode().strip()
            for line in output.splitlines():
                if unit in line and f"({channel})" in line:
                    try:
                        value_str = line.split("=")[1].replace(unit, "").strip()
                        return float(value_str)
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Could not parse value from line '{line}': {e}")
                        return None
            return None
            
        except Exception as e:
            logger.error(f"Error reading PMIC channel {channel}: {e}")
            return None

    async def get_power_readings(self) -> Dict:
        """Get power readings from all rails."""
        try:
            readings = []
            total_power = 0.0
            
            # Create tasks for all channel readings
            tasks = []
            for name, ch_current, ch_voltage in self.rails:
                current_task = asyncio.create_task(
                    self.read_pmic_channel(ch_current, "A")
                )
                voltage_task = asyncio.create_task(
                    self.read_pmic_channel(ch_voltage, "V")
                )
                tasks.append((name, current_task, voltage_task))
            
            # Wait for all readings
            for name, current_task, voltage_task in tasks:
                try:
                    current, voltage = await asyncio.gather(
                        current_task, voltage_task, return_exceptions=True
                    )
                    
                    # Handle exceptions
                    if isinstance(current, Exception):
                        current = None
                    if isinstance(voltage, Exception):
                        voltage = None
                    
                    if current is not None and voltage is not None:
                        power = voltage * current
                        readings.append({
                            "rail": name,
                            "voltage": round(voltage, 3),
                            "current": round(current, 3),
                            "power": round(power, 3)
                        })
                        total_power += power
                        
                except Exception as e:
                    logger.warning(f"Error processing readings for {name}: {e}")
                    continue
            
            return {
                "total_power": round(total_power, 3),
                "readings": readings
            }
            
        except Exception as e:
            logger.error(f"Error getting power readings: {e}")
            return {
                "total_power": 0.0,
                "readings": []
            }

# Initialize monitors
system_monitor = SystemMonitor()
power_monitor = PowerMonitor()


# Create FastAPI app
app = FastAPI(
    title="Raspberry Pi Monitor",
    description="Real-time monitoring dashboard for Raspberry Pi",
    version="1.0.0"
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def get_stats():
    """Get current system statistics."""
    try:
        stats = await system_monitor.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error in stats API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/power")
async def get_power():
    """Get current power readings."""
    try:
        power_data = await power_monitor.get_power_readings()
        return power_data
    except Exception as e:
        logger.error(f"Error in power API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}

# Shutdown endpoint
@app.post("/shutdown")
async def shutdown():
    """Shutdown the Raspberry Pi."""
    try:
        logger.info("Shutting down the system...")
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        return {"status": "shutdown initiated"}
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate shutdown")

# Reboot endpoint
@app.post("/reboot")
async def reboot():
    """Reboot the Raspberry Pi."""
    try:
        logger.info("Rebooting the system...")
        subprocess.run(["sudo", "reboot"], check=True)
        return {"status": "reboot initiated"}
    except Exception as e:
        logger.error(f"Error during reboot: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate reboot")

# Internet Speedtest endpoint
@app.get("/api/speedtest")
async def speedtest():
    """Run a speedtest and return results."""
    try:
        logger.info("Running speedtest...")
        process = await asyncio.create_subprocess_exec(
            "speedtest-cli", "--simple",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Speedtest failed: {stderr.decode()}")
            raise HTTPException(status_code=500, detail="Speedtest failed")
        
        output = stdout.decode().strip()
        results = {}
        for line in output.splitlines():
            if "Download" in line:
                results["download"] = float(line.split()[1])
            elif "Upload" in line:
                results["upload"] = float(line.split()[1])
            elif "Ping" in line:
                results["ping"] = float(line.split()[1])
        
        return results
    except Exception as e:
        logger.error(f"Error running speedtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        access_log=True,
        log_level="info"
    )
