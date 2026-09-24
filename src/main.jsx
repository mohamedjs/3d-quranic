import { createRoot } from 'react-dom/client';
import { Game } from './game/components/Game.jsx';
import './game/ui/style.css';

createRoot(document.getElementById('root')).render(<Game />);
