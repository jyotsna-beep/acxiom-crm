import React from "react";
export default function ConfirmDialog({ isOpen, title = "Confirm action", message, confirmLabel = "Confirm", onCancel, onConfirm }) {
  if (!isOpen) {
    return null;
  }
  return (
    <div className="modal d-block" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
      <div className="modal-dialog">
        <div className="modal-content shadow">
          <div className="modal-header"><h2 className="modal-title fs-5" id="confirm-dialog-title">{title}</h2></div>
          <div className="modal-body"><p className="mb-0">{message}</p></div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
            <button type="button" className="btn btn-danger" onClick={onConfirm}>{confirmLabel}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
