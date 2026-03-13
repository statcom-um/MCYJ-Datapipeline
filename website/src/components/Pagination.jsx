import React from 'react';

const DEFAULT_PAGE_SIZE = 25;

export function Pagination({ totalItems, itemsPerPage = DEFAULT_PAGE_SIZE, currentPage, onPageChange }) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);

    if (totalPages <= 1) return null;

    const startItem = (currentPage - 1) * itemsPerPage + 1;
    const endItem = Math.min(currentPage * itemsPerPage, totalItems);

    const getPageNumbers = () => {
        const pages = [];
        const maxVisible = 7;

        if (totalPages <= maxVisible) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            pages.push(1);

            if (currentPage > 3) pages.push('...');

            const start = Math.max(2, currentPage - 1);
            const end = Math.min(totalPages - 1, currentPage + 1);

            for (let i = start; i <= end; i++) pages.push(i);

            if (currentPage < totalPages - 2) pages.push('...');

            pages.push(totalPages);
        }

        return pages;
    };

    return (
        <div className="pagination">
            <div className="pagination-info">
                Showing {startItem}–{endItem} of {totalItems}
            </div>
            <div className="pagination-controls">
                <button
                    className="pagination-btn"
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                >
                    Previous
                </button>
                {getPageNumbers().map((page, idx) => (
                    page === '...' ? (
                        <span key={`ellipsis-${idx}`} className="pagination-ellipsis">...</span>
                    ) : (
                        <button
                            key={page}
                            className={`pagination-btn pagination-page ${currentPage === page ? 'active' : ''}`}
                            onClick={() => onPageChange(page)}
                        >
                            {page}
                        </button>
                    )
                ))}
                <button
                    className="pagination-btn"
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                >
                    Next
                </button>
            </div>
        </div>
    );
}

export default Pagination;
