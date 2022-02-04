import React, { useState } from 'react';
import {
  AlertGroup,
  Alert,
  AlertActionCloseButton,
  AlertVariant,
} from '@patternfly/react-core';
import { shape, arrayOf, func, string, oneOf, bool, number } from 'prop-types';

export default function useToast() {
  const [toasts, setToasts] = useState([]);

  const addToast = (newToast) => {
    setToasts((oldToasts) => [...oldToasts, newToast]);
  };

  const removeToast = (toastId) => {
    setToasts((oldToasts) => oldToasts.filter((t) => t.id !== toastId));
  };

  return {
    addToast,
    removeToast,
    Toast,
    toastProps: {
      toasts,
      removeToast,
    },
  };
}

export function Toast({ toasts, removeToast }) {
  if (!toasts.length) {
    return null;
  }

  return (
    <AlertGroup data-cy="toast-container" isToast>
      {toasts.map((toast) => (
        <Alert
          actionClose={
            <AlertActionCloseButton onClose={() => removeToast(toast.id)} />
          }
          onTimeout={() => removeToast(toast.id)}
          timeout={toast.hasTimeout}
          title={toast.title}
          variant={toast.variant}
          key={`toast-message-${toast.id}`}
          oaiaId={`toast-message-${toast.id}`}
        >
          {toast.message}
        </Alert>
      ))}
    </AlertGroup>
  );
}

const ToastType = shape({
  title: string.isRequired,
  variant: oneOf(AlertVariant.values).isRequired,
  id: oneOf([string, number]).isRequired,
  hasTimeout: bool,
  message: string,
});

Toast.propTypes = {
  toasts: arrayOf(ToastType).isRequired,
  removeToast: func.isRequired,
};

export { AlertVariant };
