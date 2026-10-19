import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@xyflow/react/dist/style.css';
import './styles.css';
import App from './App';
import Playground from './playground/Playground';
import ScenarioPlayground from './scenarios/ScenarioPlayground';
import PlanBPreview from './preview/PlanBPreview';
import NodeGrammar from './playground/grammar/NodeGrammar';

// #playground：节点视觉 A/B；#scenarios：多情景 A/B；#plan-b：方案 B 视觉预览；#grammar：节点视觉（一个通道一个问题）A/B；其余都是应用本身。
function Root() {
  const [hash, setHash] = useState(location.hash);
  useEffect(() => {
    const onHash = () => setHash(location.hash);
    addEventListener('hashchange', onHash);
    return () => removeEventListener('hashchange', onHash);
  }, []);
  if (hash === '#playground') return <Playground />;
  if (hash === '#scenarios') return <ScenarioPlayground />;
  if (hash === '#plan-b') return <PlanBPreview />;
  if (hash === '#grammar') return <NodeGrammar />;
  return <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
