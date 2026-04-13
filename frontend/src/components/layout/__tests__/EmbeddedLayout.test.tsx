import { render, screen, fireEvent } from '@testing-library/react';
import EmbeddedLayout from '../EmbeddedLayout';

describe('EmbeddedLayout', () => {
  it('renders children', () => {
    render(<EmbeddedLayout><p>conteúdo</p></EmbeddedLayout>);
    expect(screen.getByText('conteúdo')).toBeInTheDocument();
  });

  it('renders close button', () => {
    render(<EmbeddedLayout><p>x</p></EmbeddedLayout>);
    expect(screen.getByRole('button', { name: /fechar/i })).toBeInTheDocument();
  });

  it('sends postMessage close when button is clicked', () => {
    const postMessageSpy = jest.spyOn(window.parent, 'postMessage');
    render(<EmbeddedLayout><p>x</p></EmbeddedLayout>);
    fireEvent.click(screen.getByRole('button', { name: /fechar/i }));
    expect(postMessageSpy).toHaveBeenCalledWith('wpp:close', '*');
    postMessageSpy.mockRestore();
  });
});
