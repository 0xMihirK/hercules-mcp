import asyncio
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager

async def test_all():
    config = HerculesConfig.from_env()
    docker = DockerManager(config)
    
    print("Starting container...")
    await docker.start_container()
    
    print("--- Testing File Tools ---")
    await docker.write_file("/opt/workspace/test_file.txt", "Hello World\nLine 2")
    content = await docker.read_file("/opt/workspace/test_file.txt")
    print(f"Read content: {content!r}")
    
    print("--- Testing Infinite Loop Kill ---")
    # Write an infinite loop python script
    inf_loop_py = "import time\nwhile True:\n    print('still running')\n    time.sleep(1)"
    await docker.write_file("/opt/workspace/py/loop.py", inf_loop_py)
    
    # Run it in background
    job_id = "test_loop_123"
    await docker.exec_background("python3 /opt/workspace/py/loop.py", job_id)
    print("Started background job.")
    
    # Check it
    await asyncio.sleep(2)
    status = await docker.check_job(job_id)
    print("Job status after 2s:", status)
    
    # Kill it
    killed = await docker.kill_job(job_id)
    print("Kill result:", killed)
    
    # Check again
    await asyncio.sleep(1)
    status_after = await docker.check_job(job_id)
    print("Job status after kill:", status_after)

    # Clean shutdown
    print("--- Testing Container Shutdown ---")
    await docker.stop_container()
    print("Container stopped.")

if __name__ == "__main__":
    asyncio.run(test_all())
