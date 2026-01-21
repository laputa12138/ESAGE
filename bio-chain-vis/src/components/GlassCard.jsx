import React from 'react';
import clsx from 'clsx';

export const GlassCard = ({ children, className, onClick }) => {
    return (
        <div
            onClick={onClick}
            className={clsx(
                "bg-white/80 backdrop-blur-md border border-white/20 shadow-md rounded-xl p-6 transition-all duration-200",
                "hover:shadow-lg hover:-translate-y-0.5",
                onClick && "cursor-pointer",
                className
            )}
        >
            {children}
        </div>
    );
};
