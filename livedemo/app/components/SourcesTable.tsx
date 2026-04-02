"use client";

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFacetedMinMaxValues,
  flexRender,
  createColumnHelper,
  type ColumnFiltersState,
  type SortingState,
  type FilterFn,
} from "@tanstack/react-table";
import type { RankedSource } from "@/app/types";
import {
  LEAN_COLORS,
  STAKEHOLDER_LABELS,
  formatLean,
  formatFrame,
} from "@/app/lib/format";
import { ColumnFilter } from "./ColumnFilter";

const arrIncludesSome: FilterFn<RankedSource> = (
  row,
  columnId,
  filterValue: string[],
) => {
  if (!filterValue || filterValue.length === 0) return true;
  const rowValues = row.getValue<string[]>(columnId);
  return filterValue.some((v) => rowValues.includes(v));
};

const col = createColumnHelper<RankedSource>();

function SortIcon({ direction }: { direction: false | "asc" | "desc" }) {
  if (!direction) {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="opacity-30">
        <path d="M6 2.5L8.5 5.5H3.5L6 2.5Z" fill="currentColor" />
        <path d="M6 9.5L3.5 6.5H8.5L6 9.5Z" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-accent">
      {direction === "asc" ? (
        <path d="M6 3L9 7H3L6 3Z" fill="currentColor" />
      ) : (
        <path d="M6 9L3 5H9L6 9Z" fill="currentColor" />
      )}
    </svg>
  );
}

export function SourcesTable({ data }: { data: RankedSource[] }) {
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo(
    () => [
      col.accessor((row) => row.source.title, {
        id: "title",
        header: "Title",
        cell: (info) => (
          <div>
            <a
              href={info.row.original.source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-accent transition-colors font-medium"
            >
              {info.getValue()}
            </a>
            <span className="block text-[11px] font-mono text-zinc-400 dark:text-zinc-500 mt-0.5">
              {info.row.original.source.source}
            </span>
          </div>
        ),
        meta: { filterVariant: "text" as const },
        minSize: 260,
      }),
      col.accessor((row) => row.annotation.stance_summary, {
        id: "stance_summary",
        header: "Stance",
        cell: (info) => (
          <span
            className="text-zinc-500 dark:text-zinc-400 line-clamp-2"
            title={info.getValue()}
          >
            {info.getValue()}
          </span>
        ),
        meta: { filterVariant: "text" as const },
        minSize: 200,
      }),
      col.accessor((row) => row.source.published_at, {
        id: "published_at",
        header: "Published",
        cell: (info) => (
          <span className="text-zinc-500 dark:text-zinc-400 whitespace-nowrap">
            {info.getValue() ?? "—"}
          </span>
        ),
        meta: { filterVariant: "text" as const },
        minSize: 120,
      }),
      col.accessor((row) => row.annotation.political_lean, {
        id: "political_lean",
        header: "Lean",
        cell: (info) => {
          const lean =
            LEAN_COLORS[info.getValue()] ?? LEAN_COLORS.center;
          return (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium whitespace-nowrap ${lean.bg} ${lean.text}`}
            >
              {formatLean(info.getValue())}
            </span>
          );
        },
        meta: {
          filterVariant: "select" as const,
          formatValue: formatLean,
        },
        minSize: 110,
      }),
      col.accessor((row) => row.annotation.stakeholder_type, {
        id: "stakeholder_type",
        header: "Stakeholder",
        cell: (info) => (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300 whitespace-nowrap">
            {STAKEHOLDER_LABELS[info.getValue()] ?? info.getValue()}
          </span>
        ),
        meta: {
          filterVariant: "select" as const,
          formatValue: (v: string) => STAKEHOLDER_LABELS[v] ?? v,
        },
        minSize: 120,
      }),
      col.accessor((row) => row.annotation.policy_frames, {
        id: "policy_frames",
        header: "Frames",
        cell: (info) => (
          <div className="flex flex-wrap gap-1">
            {info.getValue().map((frame) => (
              <span
                key={frame}
                className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 whitespace-nowrap"
              >
                {formatFrame(frame)}
              </span>
            ))}
          </div>
        ),
        filterFn: arrIncludesSome,
        meta: {
          filterVariant: "multi-select" as const,
          formatValue: formatFrame,
        },
        enableSorting: false,
        minSize: 180,
      }),
      col.accessor((row) => row.annotation.topic, {
        id: "topic",
        header: "Topic",
        cell: (info) => (
          <span className="text-zinc-500 dark:text-zinc-400">
            {info.getValue()}
          </span>
        ),
        meta: { filterVariant: "select" as const },
        minSize: 140,
      }),
      col.accessor((row) => row.annotation.geographic_focus, {
        id: "geographic_focus",
        header: "Geo Focus",
        cell: (info) => (
          <span className="text-zinc-500 dark:text-zinc-400 whitespace-nowrap">
            {info.getValue()}
          </span>
        ),
        meta: { filterVariant: "select" as const },
        minSize: 130,
      }),
      col.accessor("relevance_score", {
        header: "Relevance",
        cell: (info) => {
          const pct = (info.getValue() * 100).toFixed(0);
          return (
            <div className="flex items-center gap-2">
              <div className="w-12 h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs tabular-nums font-mono text-zinc-500 dark:text-zinc-400">
                {pct}%
              </span>
            </div>
          );
        },
        meta: { filterVariant: "range" as const },
        minSize: 120,
      }),
    ],
    [],
  );

  const table = useReactTable({
    data,
    columns,
    state: { columnFilters, sorting },
    onColumnFiltersChange: setColumnFilters,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    getFacetedMinMaxValues: getFacetedMinMaxValues(),
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr
              key={headerGroup.id}
              className="bg-zinc-50 dark:bg-zinc-900/50"
            >
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  colSpan={header.colSpan}
                  className="px-3 py-2.5 text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400 whitespace-nowrap"
                  style={{ minWidth: header.column.columnDef.minSize }}
                >
                  {header.isPlaceholder ? null : (
                    <div
                      className={
                        header.column.getCanSort()
                          ? "flex items-center gap-1 cursor-pointer select-none"
                          : "flex items-center gap-1"
                      }
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {header.column.getCanSort() && (
                        <SortIcon direction={header.column.getIsSorted()} />
                      )}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          ))}
          {/* Filter row */}
          <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30">
            {table.getHeaderGroups()[0].headers.map((header) => (
              <th key={header.id} className="px-3 py-1.5">
                {header.column.getCanFilter() ? (
                  <ColumnFilter column={header.column} table={table} />
                ) : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {table.getRowModel().rows.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="px-3 py-8 text-center text-zinc-400 dark:text-zinc-500"
              >
                No results match the current filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
