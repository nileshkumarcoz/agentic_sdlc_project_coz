import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import Form from './index';
import * as formService from '../../services/formService';

expect.extend(toHaveNoViolations);

jest.mock('../../services/formService');

const VALID_PAYLOAD = {
  firstName: 'Jane',
  lastName: 'Doe',
  email: 'jane@example.com',
  category: 'General',
  consentGiven: true,
};

async function fillAndSubmit(overrides = {}) {
  const data = { ...VALID_PAYLOAD, ...overrides };
  if (data.firstName) await userEvent.type(screen.getByLabelText(/first name/i), data.firstName);
  if (data.lastName) await userEvent.type(screen.getByLabelText(/last name/i), data.lastName);
  if (data.email) await userEvent.type(screen.getByLabelText(/email/i), data.email);
  if (data.category) await userEvent.selectOptions(screen.getByLabelText(/category/i), data.category);
  if (data.consentGiven) await userEvent.click(screen.getByLabelText(/consent/i));
  await userEvent.click(screen.getByRole('button', { name: /submit/i }));
}

describe('Form', () => {
  beforeEach(() => jest.clearAllMocks());

  it('UT-01: renders all fields with labels', () => {
    render(<Form />);
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/consent/i)).toBeInTheDocument();
  });

  it('UT-03: shows inline errors when required fields are empty on submit', async () => {
    render(<Form />);
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    await waitFor(() => {
      expect(screen.getByText('First name is required')).toBeInTheDocument();
      expect(screen.getByText('Email is required')).toBeInTheDocument();
      expect(screen.getByText('Please select a category')).toBeInTheDocument();
    });
  });

  it('UT-04: shows error for invalid email', async () => {
    render(<Form />);
    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    await waitFor(() => expect(screen.getByText('Enter a valid email')).toBeInTheDocument());
  });

  it('UT-05: disables submit button while submitting', async () => {
    let resolve;
    formService.submitForm.mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<Form />);
    await fillAndSubmit();
    await waitFor(() => expect(screen.getByRole('button', { name: /submitting/i })).toBeDisabled());
    resolve({ submissionId: 'abc-123', message: 'ok' });
  });

  it('UT-06: shows success banner on 201 response', async () => {
    formService.submitForm.mockResolvedValue({ submissionId: 'abc-123', message: 'ok' });
    render(<Form />);
    await fillAndSubmit();
    await waitFor(() => expect(screen.getByTestId('success-banner')).toBeInTheDocument());
  });

  it('UT-07: shows error banner on API failure; form preserved', async () => {
    formService.submitForm.mockRejectedValue(new Error('Server error'));
    render(<Form />);
    await fillAndSubmit();
    await waitFor(() => expect(screen.getByTestId('error-banner')).toBeInTheDocument());
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
  });

  it('UT-08: calls submitForm with correct payload', async () => {
    formService.submitForm.mockResolvedValue({ submissionId: 'xyz' });
    render(<Form />);
    await fillAndSubmit();
    await waitFor(() =>
      expect(formService.submitForm).toHaveBeenCalledWith(
        expect.objectContaining({ firstName: 'Jane', email: 'jane@example.com' })
      )
    );
  });

  it('a11y: no axe violations on initial render', async () => {
    const { container } = render(<Form />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
