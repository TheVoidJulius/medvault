import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});

// jsdom has no layout engine; navigation calls scrollTo after every route change.
window.scrollTo = (() => undefined) as typeof window.scrollTo;
