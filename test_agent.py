from agent import run_agent_task
import time

def main():
    # 1. The question you want to ask your agent
    question = "Is it safe to consume high amounts of caffeine if I have a heart condition?"
    
    print(f"🚀 Sending query to Cardia: '{question}'")
    
    # 2. .delay() sends the task to Redis. It returns immediately with a task object.
    task = run_agent_task.delay(question)
    
    print(f"📨 Task submitted! ID: {task.id}")
    print("⏳ Cardia is researching, drafting, and self-reviewing...")

    # 3. Keep checking if the agent is done
    start_time = time.time()
    while not task.ready():
        # This loop simulates the "Loading" spinner on a phone app
        elapsed = int(time.time() - start_time)
        print(f"⌛ {elapsed}s: Reviewer is checking for accuracy...", end="\r")
        time.sleep(1)

    # 4. Get the final result once task.ready() is True
    print("\n\n✅ --- FINAL RESPONSE FROM AGENT ---")
    print(task.result)

if __name__ == "__main__":
    main()