import { RouterProvider } from '@tanstack/react-router';
import { router } from './router';
import { WorkspaceProvider } from './workspace/WorkspaceContext';
import './styles.css';

function App() {
  return (
    <WorkspaceProvider>
      <RouterProvider router={router} />
    </WorkspaceProvider>
  );
}

export default App;
