/**
 * Streaming accumulation logic tests for the voice agent transcript pipeline.
 *
 * These tests exercise the pure accumulation logic (sanitizeDialogueText +
 * the chunkSeparator + TurnAccumulator protocol) without requiring a DOM,
 * React, WebSocket, or AudioContext. They verify:
 *
 *  1. Multiple streamed chunks produce ONE complete transcript entry.
 *  2. display.content accumulates (not replaced) across chunks.
 *  3. AgentAudioDone mid-turn does NOT lose accumulated content.
 *  4. A user ConversationText closes the turn and starts a fresh one.
 *  5. Duplicate message IDs are de-duplicated (idempotency).
 *  6. The separator logic picks space vs double-newline correctly.
 *  7. sanitizeDialogueText strips emojis, asterisks, and heading markers.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { sanitizeDialogueText } from '../hooks/useVoiceAgent';

// ── Re-implement the pure accumulation logic in isolation ─────────────────────
// We copy just enough logic from useVoiceAgent to test it without React/DOM.

type TranscriptEntry = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  display?: { format: 'markdown'; content: string };
  speech?: { text: string };
};

interface Turn {
  id: string;
  open: boolean;
  seenMsgIds: Set<string>;
}

function freshTurn(): Turn {
  return { id: '', open: false, seenMsgIds: new Set() };
}

function uuid(n: number): string { return `turn-${n}`; }

function chunkSeparator(existing: string, incoming: string): string {
  const isBulletOrList = /^[-*•]\s+|^\d+\.\s+/.test(incoming.trim());
  const prevEndsWithBreak = /[:\n]$/.test(existing.trim());
  return (isBulletOrList || prevEndsWithBreak) ? '\n\n' : ' ';
}

class TranscriptAccumulator {
  private entries: TranscriptEntry[] = [];
  private turn: Turn = freshTurn();
  private idCounter = 0;

  openAssistantTurn(): string {
    if (!this.turn.open) {
      this.turn = { id: uuid(++this.idCounter), open: true, seenMsgIds: new Set() };
    }
    return this.turn.id;
  }

  closeAssistantTurn() {
    this.turn = freshTurn();
  }

  appendAssistantChunk(content: string, display?: string, speech?: string, msgId?: string) {
    const turnId = this.openAssistantTurn();

    // Idempotency: skip duplicate message IDs for this turn
    if (msgId) {
      if (this.turn.seenMsgIds.has(msgId)) return;
      this.turn.seenMsgIds.add(msgId);
    }

    this.turn.id = turnId; // ensure id is set

    const cleanContent = sanitizeDialogueText(content);
    const cleanDisplay = display ? sanitizeDialogueText(display) : undefined;
    const cleanSpeech  = speech  ? sanitizeDialogueText(speech)  : undefined;

    const last = this.entries[this.entries.length - 1];
    if (last && last.role === 'assistant' && last.id === turnId) {
      const sep = chunkSeparator(last.content, cleanContent);
      const updatedContent = `${last.content}${sep}${cleanContent}`.trim();
      const existingDisplay = last.display?.content || '';
      const updatedDisplay = cleanDisplay
        ? { format: 'markdown' as const, content: existingDisplay ? `${existingDisplay}${sep}${cleanDisplay}`.trim() : cleanDisplay }
        : last.display;
      const updatedSpeech = cleanSpeech
        ? { text: `${last.speech?.text || last.content} ${cleanSpeech}`.trim() }
        : last.speech;
      this.entries[this.entries.length - 1] = { ...last, content: updatedContent, display: updatedDisplay, speech: updatedSpeech };
    } else {
      this.entries.push({
        id: turnId,
        role: 'assistant',
        content: cleanContent,
        display: cleanDisplay ? { format: 'markdown', content: cleanDisplay } : undefined,
        speech: cleanSpeech ? { text: cleanSpeech } : undefined,
      });
    }
  }

  appendUserMessage(text: string) {
    this.closeAssistantTurn();
    const clean = sanitizeDialogueText(text) || text;
    const last = this.entries[this.entries.length - 1];
    if (last && last.role === 'user' && last.content.trim().toLowerCase() === clean.trim().toLowerCase()) return;
    this.entries.push({ id: `user-${++this.idCounter}`, role: 'user', content: clean });
  }

  /** Simulate AgentAudioDone — should NOT reset turn or lose content. */
  onAgentAudioDone() {
    // Turn stays open. Only TTS boundary, not conversation boundary.
    // (No-op in this accumulator — matches the hook behaviour.)
  }

  getEntries(): TranscriptEntry[] { return this.entries; }
  getLastEntry(): TranscriptEntry | undefined { return this.entries[this.entries.length - 1]; }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('sanitizeDialogueText', () => {
  it('strips markdown bold asterisks', () => {
    expect(sanitizeDialogueText('**bold** text')).toBe('bold text');
  });

  it('strips heading markers', () => {
    expect(sanitizeDialogueText('## Speed of Light\nIt is fast.')).toBe('Speed of Light\nIt is fast.');
  });

  it('strips Unicode emoji', () => {
    const result = sanitizeDialogueText('Hello 😊 world');
    expect(result).not.toContain('😊');
    expect(result).toContain('Hello');
  });

  it('collapses double spaces', () => {
    expect(sanitizeDialogueText('hello  world')).toBe('hello world');
  });

  it('returns empty string for falsy input', () => {
    expect(sanitizeDialogueText('')).toBe('');
    expect(sanitizeDialogueText(undefined as any)).toBe('');
  });
});

describe('chunkSeparator', () => {
  it('uses space for prose continuation', () => {
    expect(chunkSeparator('The speed of light is fast.', 'Another expression')).toBe(' ');
  });

  it('uses double newline when incoming is a bullet', () => {
    expect(chunkSeparator('Here are the formulas:', '- E = mc²')).toBe('\n\n');
  });

  it('uses double newline when previous ends with colon', () => {
    expect(chunkSeparator('There are three:',  'First item')).toBe('\n\n');
  });

  it('uses double newline when incoming is numbered list', () => {
    expect(chunkSeparator('Here you go.', '1. First')).toBe('\n\n');
  });
});

describe('TranscriptAccumulator: streaming accumulation', () => {
  let acc: TranscriptAccumulator;

  beforeEach(() => { acc = new TranscriptAccumulator(); });

  it('produces exactly one entry for a single-chunk response', () => {
    acc.appendAssistantChunk('The speed of light is 299,792,458 m/s.');
    expect(acc.getEntries()).toHaveLength(1);
    expect(acc.getEntries()[0].role).toBe('assistant');
  });

  it('accumulates multiple chunks into one entry — the "Another..." bug', () => {
    acc.appendAssistantChunk(
      'The speed of light is approximately 299,792,458 metres per second.',
      'The speed of light is approximately 299,792,458 metres per second.',
    );
    acc.appendAssistantChunk(
      'Another expression comes from electromagnetism: c = 1/√(ε₀μ₀).',
      'Another expression comes from electromagnetism: c = 1/√(ε₀μ₀).',
    );

    const entries = acc.getEntries();
    expect(entries).toHaveLength(1);                          // ONE entry
    expect(entries[0].content).toContain('299,792,458');      // first chunk preserved
    expect(entries[0].content).toContain('Another');          // second chunk present
    expect(entries[0].display?.content).toContain('299,792,458'); // display accumulated
    expect(entries[0].display?.content).toContain('Another');
  });

  it('all chunks share the same stable entry id', () => {
    acc.appendAssistantChunk('Chunk one.');
    acc.appendAssistantChunk('Chunk two.');
    acc.appendAssistantChunk('Chunk three.');
    const entries = acc.getEntries();
    expect(entries).toHaveLength(1);
    expect(entries[0].id).toBe('turn-1');
  });

  it('AgentAudioDone between chunks does NOT lose content', () => {
    acc.appendAssistantChunk('The speed of light is 299,792,458 m/s.');
    acc.onAgentAudioDone(); // TTS segment boundary — turn must stay open
    acc.appendAssistantChunk('Another expression: c = 1/√(ε₀μ₀).');

    const entries = acc.getEntries();
    expect(entries).toHaveLength(1);
    expect(entries[0].content).toContain('299,792,458');
    expect(entries[0].content).toContain('Another');
  });

  it('multiple AgentAudioDone events between chunks still produce one entry', () => {
    acc.appendAssistantChunk('Part one.');
    acc.onAgentAudioDone();
    acc.appendAssistantChunk('Part two.');
    acc.onAgentAudioDone();
    acc.appendAssistantChunk('Part three.');
    acc.onAgentAudioDone();

    expect(acc.getEntries()).toHaveLength(1);
    const content = acc.getEntries()[0].content;
    expect(content).toContain('Part one');
    expect(content).toContain('Part two');
    expect(content).toContain('Part three');
  });

  it('user ConversationText closes the turn and starts a fresh one', () => {
    acc.appendAssistantChunk('The answer is 42.');
    acc.appendUserMessage('What about light speed?');
    acc.appendAssistantChunk('It is 299,792,458 m/s.');

    const entries = acc.getEntries();
    expect(entries).toHaveLength(3); // assistant, user, assistant
    expect(entries[0].role).toBe('assistant');
    expect(entries[1].role).toBe('user');
    expect(entries[2].role).toBe('assistant');
    expect(entries[0].id).not.toBe(entries[2].id); // different turn IDs
  });

  it('display.content is accumulated across chunks, not replaced', () => {
    acc.appendAssistantChunk('Chunk A.', 'Display A.');
    acc.appendAssistantChunk('Chunk B.', 'Display B.');
    acc.appendAssistantChunk('Chunk C.', 'Display C.');

    const entry = acc.getLastEntry()!;
    expect(entry.display?.content).toContain('Display A');
    expect(entry.display?.content).toContain('Display B');
    expect(entry.display?.content).toContain('Display C');
  });

  it('first chunk with no display still accumulates later display chunks', () => {
    acc.appendAssistantChunk('Plain speech.', undefined);
    acc.appendAssistantChunk('Next bit.', 'Next bit with *markdown*.');

    const entry = acc.getLastEntry()!;
    // After sanitize, asterisks are stripped
    expect(entry.display?.content).not.toContain('*markdown*');
    expect(entry.display?.content).toContain('Next bit with');
  });

  it('no text is lost or duplicated across 10 rapid chunks', () => {
    const sentences = Array.from({ length: 10 }, (_, i) => `Sentence ${i + 1} here.`);
    sentences.forEach((s) => acc.appendAssistantChunk(s, s));

    const entry = acc.getLastEntry()!;
    sentences.forEach((s) => {
      const count = (entry.content.match(new RegExp(s.replace('.', '\\.'), 'g')) || []).length;
      expect(count).toBe(1); // each sentence appears exactly once
    });
    expect(acc.getEntries()).toHaveLength(1);
  });
});

describe('TranscriptAccumulator: idempotency', () => {
  let acc: TranscriptAccumulator;
  beforeEach(() => { acc = new TranscriptAccumulator(); });

  it('ignores duplicate message IDs', () => {
    acc.appendAssistantChunk('Hello.', 'Hello.', undefined, 'msg-001');
    acc.appendAssistantChunk('Hello.', 'Hello.', undefined, 'msg-001'); // duplicate
    acc.appendAssistantChunk('World.', 'World.', undefined, 'msg-002');

    const entry = acc.getLastEntry()!;
    // "Hello" must appear exactly once in content
    const helloCount = (entry.content.match(/Hello/g) || []).length;
    expect(helloCount).toBe(1);
    expect(entry.content).toContain('World');
  });

  it('duplicate user messages are de-duplicated (optimistic inject vs echo)', () => {
    acc.appendUserMessage('what is the speed of light');
    acc.appendUserMessage('what is the speed of light'); // WebSocket echo

    expect(acc.getEntries()).toHaveLength(1);
  });
});

describe('TranscriptAccumulator: multi-turn sequence', () => {
  it('correctly handles question → answer → question → answer cycle', () => {
    const acc = new TranscriptAccumulator();

    acc.appendUserMessage('What is light?');
    acc.appendAssistantChunk('Light is electromagnetic radiation.');
    acc.appendAssistantChunk('It travels at 299,792,458 m/s.');
    acc.onAgentAudioDone();

    acc.appendUserMessage('Give me the formula.');
    acc.appendAssistantChunk('The formula is c = λf.');
    acc.appendAssistantChunk('Where λ is wavelength and f is frequency.');

    const entries = acc.getEntries();
    expect(entries).toHaveLength(4); // user, assistant, user, assistant

    const firstAnswer = entries[1];
    expect(firstAnswer.content).toContain('electromagnetic');
    expect(firstAnswer.content).toContain('299,792,458');

    const secondAnswer = entries[3];
    expect(secondAnswer.content).toContain('c = λf');
    expect(secondAnswer.content).toContain('wavelength');

    // Each assistant entry has a different ID
    expect(firstAnswer.id).not.toBe(secondAnswer.id);
  });
});
