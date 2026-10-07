import React from "react";
export default function Pagination({ page = 1, pageCount = 1, onPageChange }) {
  if (pageCount <= 1) {
    return null;
  }
  return (
    <nav aria-label="Pagination">
      <ul className="pagination mb-0">
        <li className={`page-item ${page <= 1 ? "disabled" : ""}`}><button className="page-link" type="button" onClick={() => onPageChange(page - 1)}>Previous</button></li>
        <li className="page-item disabled"><span className="page-link">Page {page} of {pageCount}</span></li>
        <li className={`page-item ${page >= pageCount ? "disabled" : ""}`}><button className="page-link" type="button" onClick={() => onPageChange(page + 1)}>Next</button></li>
      </ul>
    </nav>
  );
}
