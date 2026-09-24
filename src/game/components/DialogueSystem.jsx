// <DialogueSystem/>: owns the story runner that plays an encounter's steps in the DOM
// dialogue overlay (text, choices, questions, illustrations), and hands verses/rewards
// to the game. Character lines may use speech synthesis; Quran never does.
import { useLayoutEffect } from 'react';
import { Story } from '../systems/story.js';
import { Voice } from '../systems/audio.js';
import { refs } from '../systems/refs.js';

export function DialogueSystem() {
  useLayoutEffect(() => {
    refs.dialogue = new Story({
      lang: () => refs.game?.lang() ?? 'ar',
      hooks: { verses: step => refs.game.recite(step), reward: enc => refs.game.grant(enc), speaker: id => refs.game?.speaker?.(id) },
    });
    return () => { Voice.cancel(); refs.dialogue = null; };
  }, []);
  return null;
}
