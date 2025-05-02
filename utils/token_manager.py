# utils/token_manager.py
def estimate_tokens(text: str) -> int:
    return len(text) 

def build_window(history, remix_tag="<REMIXED>", budget=600):
    window = []
    used = estimate_tokens(remix_tag)
    
    for i in range(len(history - 1, -1, -1):
        m = history[i]
        
        if m["role"] == "system":
            continue

        cost = estimate_tokens(m["content"])
        if used + cost > budget:
            break
        used += cost 
        window.append(m)
    return [{"role": "system", "content": remix_tag}] + list(reversed(window))