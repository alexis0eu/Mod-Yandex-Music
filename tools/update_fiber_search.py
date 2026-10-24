import os

target = r"src\renderer\mod-renderer.js"
with open(target, "r", encoding="utf-8") as f:
    c = f.read()

old_block = """  // ==========================================
  // 5. REACT FIBER TRAVERSAL HELPERS
  // ==========================================
  function findFiberNode(element) {
    if (!element) return null;
    const fiberKey = Object.keys(element).find((key) => key.startsWith("__reactFiber$") || key.startsWith("__reactInternalInstance$"));
    return fiberKey ? element[fiberKey] : null;
  }

  function extractSonataStateFromFiber(element) {
    if (!element) return null;
    try {
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;

      const visited = new Set();
      const queue = [fiberNode];
      let steps = 0;

      while (queue.length > 0 && steps < 200) {
        steps++;
        const curr = queue.shift();
        if (!curr || visited.has(curr)) continue;
        visited.add(curr);

        // Check memoizedProps
        if (curr.memoizedProps) {
          if (curr.memoizedProps.sonataState && curr.memoizedProps.sonataState.entityMeta) {
            return curr.memoizedProps.sonataState;
          }
          if (curr.memoizedProps.entityMeta && (curr.memoizedProps.entityMeta.title || curr.memoizedProps.entityMeta.id)) {
            return {
              entityMeta: curr.memoizedProps.entityMeta,
              isPlaying: curr.memoizedProps.isPlaying,
              position: curr.memoizedProps.position,
              duration: curr.memoizedProps.duration
            };
          }
          if (curr.memoizedProps.track && (curr.memoizedProps.track.title || curr.memoizedProps.track.id)) {
            return {
              entityMeta: curr.memoizedProps.track,
              isPlaying: curr.memoizedProps.isPlaying,
              position: curr.memoizedProps.position,
              duration: curr.memoizedProps.duration
            };
          }
        }

        // Check memoizedState (React hooks linked list)
        let hook = curr.memoizedState;
        let hCount = 0;
        while (hook && hCount < 25) {
          hCount++;
          if (hook.memoizedState && typeof hook.memoizedState === "object") {
            const ms = hook.memoizedState;
            if (ms.sonataState && ms.sonataState.entityMeta) {
              return ms.sonataState;
            }
            if (ms.entityMeta && (ms.entityMeta.title || ms.entityMeta.id)) {
              return ms;
            }
          }
          hook = hook.next;
        }

        if (curr.child) queue.push(curr.child);
        if (curr.sibling) queue.push(curr.sibling);
        if (curr.return && steps < 40) queue.push(curr.return);
      }
      return null;
    } catch (e) {
      return null;
    }
  }"""

new_block = """  // ==========================================
  // 5. REACT FIBER TRAVERSAL HELPERS (STEPHANZION ENGINE)
  // ==========================================
  function findFiberNode(element) {
    if (!element) return null;
    const fiberKey = Object.keys(element).find((key) => key.startsWith("__reactFiber$") || key.startsWith("__reactInternalInstance$"));
    return fiberKey ? element[fiberKey] : null;
  }

  function getRootFiber(fiber) {
    let current = fiber;
    while (current && current.return) {
      current = current.return;
    }
    return current || null;
  }

  function traverseFiber(fiber, isFoundCallback, depth = 0) {
    if (!fiber || depth > 250) return null;
    const result = isFoundCallback(fiber, depth);
    if (result !== null && result !== undefined) return result;

    if (fiber.child) {
      const childResult = traverseFiber(fiber.child, isFoundCallback, depth + 1);
      if (childResult !== null && childResult !== undefined) return childResult;
    }
    if (fiber.sibling) {
      const siblingResult = traverseFiber(fiber.sibling, isFoundCallback, depth);
      if (siblingResult !== null && siblingResult !== undefined) return siblingResult;
    }
    return null;
  }

  function searchFiberProperty(element, property) {
    if (!element) return null;
    try {
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;
      const root = getRootFiber(fiberNode);
      return traverseFiber(root, (fiber) => {
        if (fiber.memoizedProps && Object.prototype.hasOwnProperty.call(fiber.memoizedProps, property)) {
          return fiber.memoizedProps;
        }
        return null;
      });
    } catch (e) {
      return null;
    }
  }

  function extractSonataStateFromFiber(element) {
    if (!element) return null;
    try {
      // 1. Direct search from root fiber for entityMeta
      const entityMetaProps = searchFiberProperty(element, "entityMeta");
      if (entityMetaProps && entityMetaProps.entityMeta) {
        const timecodeProps = searchFiberProperty(element, "timecodeClassName") || searchFiberProperty(element, "currentTimecodeClassName");
        return {
          entityMeta: entityMetaProps.entityMeta,
          isPlaying: entityMetaProps.isPlaying,
          position: timecodeProps && timecodeProps.position !== undefined ? timecodeProps.position : entityMetaProps.position,
          duration: timecodeProps && timecodeProps.duration !== undefined ? timecodeProps.duration : entityMetaProps.duration
        };
      }

      // 2. Queue-based local search fallback
      const fiberNode = findFiberNode(element);
      if (!fiberNode) return null;

      const visited = new Set();
      const queue = [fiberNode];
      let steps = 0;

      while (queue.length > 0 && steps < 150) {
        steps++;
        const curr = queue.shift();
        if (!curr || visited.has(curr)) continue;
        visited.add(curr);

        if (curr.memoizedProps) {
          if (curr.memoizedProps.sonataState && curr.memoizedProps.sonataState.entityMeta) {
            return curr.memoizedProps.sonataState;
          }
          if (curr.memoizedProps.entityMeta && (curr.memoizedProps.entityMeta.title || curr.memoizedProps.entityMeta.id)) {
            return {
              entityMeta: curr.memoizedProps.entityMeta,
              isPlaying: curr.memoizedProps.isPlaying,
              position: curr.memoizedProps.position,
              duration: curr.memoizedProps.duration
            };
          }
          if (curr.memoizedProps.track && (curr.memoizedProps.track.title || curr.memoizedProps.track.id)) {
            return {
              entityMeta: curr.memoizedProps.track,
              isPlaying: curr.memoizedProps.isPlaying,
              position: curr.memoizedProps.position,
              duration: curr.memoizedProps.duration
            };
          }
        }

        if (curr.child) queue.push(curr.child);
        if (curr.sibling) queue.push(curr.sibling);
        if (curr.return && steps < 40) queue.push(curr.return);
      }
      return null;
    } catch (e) {
      return null;
    }
  }"""

c_norm = c.replace("\r\n", "\n")
old_norm = old_block.replace("\r\n", "\n")
new_norm = new_block.replace("\r\n", "\n")

if old_norm in c_norm:
    c_norm = c_norm.replace(old_norm, new_norm)
    with open(target, "w", encoding="utf-8") as f:
        f.write(c_norm)
    print("Updated extractSonataStateFromFiber with Stephanzion searchProperty engine")
else:
    print("Could not match old_norm block")
