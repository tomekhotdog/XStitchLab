import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Library } from './pages/Library';
import { Editor } from './pages/Editor';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Library />} />
        <Route path="/d/:slug" element={<Editor />} />
      </Routes>
    </BrowserRouter>
  );
}
