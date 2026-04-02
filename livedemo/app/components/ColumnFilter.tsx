import { useState, useRef, useEffect, useMemo } from "react";
import type { Column, RowData, Table } from "@tanstack/react-table";
import { DebouncedInput } from "./DebouncedInput";
import { formatLean, formatFrame, STAKEHOLDER_LABELS } from "@/app/lib/format";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    filterVariant?: "text" | "select" | "multi-select" | "range";
    formatValue?: (value: string) => string;
  }
}

const INPUT_CLASS =
  "w-full h-7 px-2 text-xs bg-transparent border border-zinc-200 dark:border-zinc-800 rounded-md outline-none focus:border-zinc-400 dark:focus:border-zinc-600 transition-colors placeholder:text-zinc-400 dark:placeholder:text-zinc-600";

export function ColumnFilter<TData>({
  column,
  table,
}: {
  column: Column<TData, unknown>;
  table: Table<TData>;
}) {
  const { filterVariant, formatValue } = column.columnDef.meta ?? {};

  const columnFilterValue = column.getFilterValue();

  if (filterVariant === "range") {
    const minMax = column.getFacetedMinMaxValues();
    return (
      <div className="flex gap-1">
        <DebouncedInput
          type="number"
          min={Number(minMax?.[0] ?? "")}
          max={Number(minMax?.[1] ?? "")}
          value={(columnFilterValue as [number, number])?.[0] ?? ""}
          onChange={(value) =>
            column.setFilterValue((old: [number, number]) => [value, old?.[1]])
          }
          placeholder={`Min`}
          className={INPUT_CLASS + " w-16"}
          step="0.05"
        />
        <DebouncedInput
          type="number"
          min={Number(minMax?.[0] ?? "")}
          max={Number(minMax?.[1] ?? "")}
          value={(columnFilterValue as [number, number])?.[1] ?? ""}
          onChange={(value) =>
            column.setFilterValue((old: [number, number]) => [old?.[0], value])
          }
          placeholder={`Max`}
          className={INPUT_CLASS + " w-16"}
          step="0.05"
        />
      </div>
    );
  }

  if (filterVariant === "select") {
    const sortedUniqueValues = useMemo(
      () =>
        Array.from(column.getFacetedUniqueValues().keys())
          .sort()
          .slice(0, 5000),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [column.getFacetedUniqueValues()],
    );

    return (
      <select
        onChange={(e) => column.setFilterValue(e.target.value || undefined)}
        value={(columnFilterValue ?? "") as string}
        className={INPUT_CLASS + " cursor-pointer"}
      >
        <option value="">All</option>
        {sortedUniqueValues.map((value) => (
          <option value={value} key={value}>
            {formatValue ? formatValue(value) : value}
          </option>
        ))}
      </select>
    );
  }

  if (filterVariant === "multi-select") {
    return <MultiSelectFilter column={column} table={table} />;
  }

  // Default: text filter
  return (
    <DebouncedInput
      type="text"
      value={(columnFilterValue ?? "") as string}
      onChange={(value) => column.setFilterValue(value || undefined)}
      placeholder="Search..."
      className={INPUT_CLASS}
    />
  );
}

function MultiSelectFilter<TData>({
  column,
  table,
}: {
  column: Column<TData, unknown>;
  table: Table<TData>;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = (column.getFilterValue() as string[]) ?? [];

  // Flatten all array values across all pre-filtered rows to get unique individual values
  const uniqueValues = useMemo(() => {
    const allValues = table
      .getPreFilteredRowModel()
      .rows.flatMap((row) => row.getValue<string[]>(column.id));
    return [...new Set(allValues)].sort();
  }, [table, column.id]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const toggle = (value: string) => {
    const next = selected.includes(value)
      ? selected.filter((v) => v !== value)
      : [...selected, value];
    column.setFilterValue(next.length > 0 ? next : undefined);
  };

  const { formatValue } = column.columnDef.meta ?? {};

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={INPUT_CLASS + " text-left cursor-pointer flex items-center justify-between gap-1"}
      >
        <span className="truncate">
          {selected.length > 0 ? `${selected.length} selected` : "All"}
        </span>
        <svg
          width="10"
          height="10"
          viewBox="0 0 10 10"
          fill="none"
          className={`shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path
            d="M2 4L5 7L8 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 left-0 min-w-[160px] max-h-48 overflow-y-auto rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-lg py-1">
          {uniqueValues.map((value) => (
            <label
              key={value}
              className="flex items-center gap-2 px-2.5 py-1 text-xs hover:bg-zinc-50 dark:hover:bg-zinc-800/50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.includes(value)}
                onChange={() => toggle(value)}
                className="rounded border-zinc-300 dark:border-zinc-700 accent-[var(--color-accent)]"
              />
              <span className="text-foreground">
                {formatValue ? formatValue(value) : value}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
