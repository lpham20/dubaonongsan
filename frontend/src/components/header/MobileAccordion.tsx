import type { ReactNode } from "react";
import { ChevronDown } from "../icons";

type Props = {
  title: string;
  open: boolean;
  active?: boolean;
  onToggle: () => void;
  children: ReactNode;
};

export function MobileAccordion({ title, open, active, onToggle, children }: Props) {
  return (
    <div className={["mobile-accordion", open ? "open" : "", active ? "active" : ""].filter(Boolean).join(" ")}>
      <button type="button" aria-expanded={open} onClick={onToggle}>
        {title}
        <ChevronDown size={16} />
      </button>
      <div className="mobile-accordion-panel">{children}</div>
    </div>
  );
}
