import React from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import { formSchema } from '../../validation/formSchema';
import { useFormSubmit } from '../../hooks/useFormSubmit';

const CATEGORIES = ['General', 'Support', 'Billing', 'Other'];

export default function Form() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: yupResolver(formSchema) });

  const { onSubmit, isSubmitting, isSuccess, serverError } = useFormSubmit();

  if (isSuccess) {
    return (
      <div role="status" aria-live="polite" data-testid="success-banner">
        <p>Your information has been received. Thank you!</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate aria-label="Contact form">
      <p aria-hidden="true"><span aria-label="required">*</span> Required fields</p>

      {serverError && (
        <div role="alert" data-testid="error-banner">
          <p>{serverError}</p>
        </div>
      )}

      {[['firstName', 'First name'], ['lastName', 'Last name']].map(([name, label]) => (
        <div key={name}>
          <label htmlFor={name}>{label} <span aria-hidden="true">*</span></label>
          <input
            id={name}
            {...register(name)}
            aria-required="true"
            aria-describedby={errors[name] ? `${name}-error` : undefined}
          />
          {errors[name] && (
            <span id={`${name}-error`} role="alert">{errors[name].message}</span>
          )}
        </div>
      ))}

      <div>
        <label htmlFor="email">Email <span aria-hidden="true">*</span></label>
        <input
          id="email"
          type="email"
          {...register('email')}
          aria-required="true"
          aria-describedby={errors.email ? 'email-error' : undefined}
        />
        {errors.email && <span id="email-error" role="alert">{errors.email.message}</span>}
      </div>

      <div>
        <label htmlFor="phoneNumber">Phone number</label>
        <input id="phoneNumber" type="tel" {...register('phoneNumber')} />
        {errors.phoneNumber && <span role="alert">{errors.phoneNumber.message}</span>}
      </div>

      <div>
        <label htmlFor="category">Category <span aria-hidden="true">*</span></label>
        <select
          id="category"
          {...register('category')}
          aria-required="true"
          aria-describedby={errors.category ? 'category-error' : undefined}
        >
          <option value="">Select…</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {errors.category && <span id="category-error" role="alert">{errors.category.message}</span>}
      </div>

      <div>
        <label htmlFor="message">Message</label>
        <textarea id="message" {...register('message')} maxLength={500} />
        {errors.message && <span role="alert">{errors.message.message}</span>}
      </div>

      <div>
        <input
          id="consentGiven"
          type="checkbox"
          {...register('consentGiven')}
          aria-required="true"
          aria-describedby={errors.consentGiven ? 'consent-error' : undefined}
        />
        <label htmlFor="consentGiven">I consent to the processing of my data *</label>
        {errors.consentGiven && <span id="consent-error" role="alert">{errors.consentGiven.message}</span>}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting…' : 'Submit'}
      </button>
    </form>
  );
}
