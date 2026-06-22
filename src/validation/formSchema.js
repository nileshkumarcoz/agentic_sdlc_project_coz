import * as Yup from 'yup';

export const formSchema = Yup.object({
  firstName: Yup.string().required('First name is required').max(50),
  lastName: Yup.string().required('Last name is required').max(50),
  email: Yup.string().email('Enter a valid email').required('Email is required'),
  phoneNumber: Yup.string()
    .matches(/^[+]?[0-9]{7,15}$/, 'Invalid phone number')
    .optional()
    .nullable()
    .transform((v) => v || null),
  category: Yup.string().required('Please select a category'),
  message: Yup.string().max(500).optional(),
  consentGiven: Yup.boolean().oneOf([true], 'You must provide consent'),
});
