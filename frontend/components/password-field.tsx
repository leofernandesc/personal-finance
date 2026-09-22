"use client";

import { forwardRef, useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";
import { cn } from "@/lib/utils";

type PasswordFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  toggleLabel: string;
};

export const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(
  function PasswordField({ className, toggleLabel, ...props }, ref) {
    const [visible, setVisible] = useState(false);

    return (
      <div className="relative">
        <LockKeyhole
          size={17}
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-3.5 text-muted"
        />
        <input
          {...props}
          ref={ref}
          type={visible ? "text" : "password"}
          className={cn("field pl-10 pr-11", className)}
        />
        <button
          type="button"
          aria-label={`${visible ? "Ocultar" : "Mostrar"} ${toggleLabel}`}
          aria-controls={props.id}
          aria-pressed={visible}
          title={`${visible ? "Ocultar" : "Mostrar"} ${toggleLabel}`}
          onClick={() => setVisible((current) => !current)}
          className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-muted transition hover:bg-paper hover:text-ink"
        >
          {visible ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
        </button>
      </div>
    );
  },
);

PasswordField.displayName = "PasswordField";
