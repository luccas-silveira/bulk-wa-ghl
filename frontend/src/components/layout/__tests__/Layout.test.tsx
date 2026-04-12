import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Layout from '../Layout';

// react-router-dom location hooks require a router context
const renderLayout = (children = <div>Content</div>) =>
  render(
    <MemoryRouter>
      <Layout>{children}</Layout>
    </MemoryRouter>
  );

describe('Layout — skip link (FRONT-37)', () => {
  it('has a skip link pointing to #main-content', () => {
    renderLayout();
    const link = screen.getByRole('link', { name: /pular para conteúdo/i });
    expect(link).toHaveAttribute('href', '#main-content');
  });

  it('main element has id="main-content"', () => {
    renderLayout();
    const main = screen.getByRole('main');
    expect(main).toHaveAttribute('id', 'main-content');
  });
});

describe('Header — nav aria-label (FRONT-36)', () => {
  it('nav has aria-label="Navegação principal"', () => {
    renderLayout();
    const nav = screen.getByRole('navigation', { name: 'Navegação principal' });
    expect(nav).toBeInTheDocument();
  });
});
