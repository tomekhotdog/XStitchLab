/**
 * Undo/Redo manager for pattern edits
 */

export class UndoManager {
  constructor(maxHistory = 100) {
    this.undoStack = [];
    this.redoStack = [];
    this.maxHistory = maxHistory;
    this.listeners = new Set();
  }

  /**
   * Push a change to the undo stack
   * @param {Object} change - Change object with x, y, oldValue, newValue
   */
  push(change) {
    this.undoStack.push(change);

    // Clear redo stack on new change
    this.redoStack = [];

    // Limit history size
    if (this.undoStack.length > this.maxHistory) {
      this.undoStack.shift();
    }

    this.notifyListeners();
  }

  /**
   * Push multiple changes as a single undo unit
   * @param {Object[]} changes - Array of changes
   */
  pushBatch(changes) {
    if (changes.length === 0) return;

    this.undoStack.push({
      type: 'batch',
      changes: changes,
    });

    this.redoStack = [];

    if (this.undoStack.length > this.maxHistory) {
      this.undoStack.shift();
    }

    this.notifyListeners();
  }

  /**
   * Undo the last change
   * @param {Function} applyFn - Function to apply the undo (receives x, y, value, change)
   * @returns {boolean} Whether undo was performed
   */
  undo(applyFn) {
    if (this.undoStack.length === 0) return false;

    const item = this.undoStack.pop();

    if (item.type === 'batch') {
      // Undo batch in reverse order
      for (let i = item.changes.length - 1; i >= 0; i--) {
        const change = item.changes[i];
        applyFn(change.x, change.y, change.oldValue, change);
      }
      this.redoStack.push(item);
    } else if (item.type === 'backstitch') {
      // Backstitch change - pass full item
      applyFn(null, null, null, item);
      this.redoStack.push(item);
    } else {
      applyFn(item.x, item.y, item.oldValue, item);
      this.redoStack.push(item);
    }

    this.notifyListeners();
    return true;
  }

  /**
   * Redo the last undone change
   * @param {Function} applyFn - Function to apply the redo (receives x, y, value, change)
   * @returns {boolean} Whether redo was performed
   */
  redo(applyFn) {
    if (this.redoStack.length === 0) return false;

    const item = this.redoStack.pop();

    if (item.type === 'batch') {
      // Redo batch in order
      for (const change of item.changes) {
        applyFn(change.x, change.y, change.newValue, change);
      }
      this.undoStack.push(item);
    } else if (item.type === 'backstitch') {
      // Backstitch change - pass full item
      applyFn(null, null, null, item);
      this.undoStack.push(item);
    } else {
      applyFn(item.x, item.y, item.newValue, item);
      this.undoStack.push(item);
    }

    this.notifyListeners();
    return true;
  }

  /**
   * Check if undo is available
   * @returns {boolean}
   */
  canUndo() {
    return this.undoStack.length > 0;
  }

  /**
   * Check if redo is available
   * @returns {boolean}
   */
  canRedo() {
    return this.redoStack.length > 0;
  }

  /**
   * Clear all history
   */
  clear() {
    this.undoStack = [];
    this.redoStack = [];
    this.notifyListeners();
  }

  /**
   * Subscribe to state changes
   * @param {Function} listener
   */
  subscribe(listener) {
    this.listeners.add(listener);
  }

  /**
   * Unsubscribe from state changes
   * @param {Function} listener
   */
  unsubscribe(listener) {
    this.listeners.delete(listener);
  }

  /**
   * Notify listeners of state change
   */
  notifyListeners() {
    const state = {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      undoCount: this.undoStack.length,
      redoCount: this.redoStack.length,
    };
    this.listeners.forEach(listener => listener(state));
  }
}

// Singleton instance
export const undoManager = new UndoManager();
