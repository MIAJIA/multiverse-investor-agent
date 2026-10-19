import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@xyflow/react/dist/style.css';
import './styles.css';
import App from './App';
import Playground from './playground/Playground';
import ScenarioPlayground from './scenarios/ScenarioPlayground';

// #playground：节点视觉 A/B；#scenarios：多情景 A/B；其余都是应用本身。
function Root() {
  const [hash, setHash] = useState(location.hash);
  useEffect(() => {
    const onHash = () => setHash(location.hash);
    addEventListener('hashchange', onHash);
    return () => removeEventListener('hashchange', onHash);
  }, []);
  if (hash === '#playground') return <Playground />;
  if (hash === '#scenarios') return <ScenarioPlayground />;
  return <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
