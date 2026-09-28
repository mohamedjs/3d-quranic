import { createRoot } from 'react-dom/client';
import { Game } from './game/components/Game.jsx';
import './game/ui/style.css';
import './pwa/pwa.js';          // listens for beforeinstallprompt from the first moment

createRoot(document.getElementById('root')).render(<Game />);
