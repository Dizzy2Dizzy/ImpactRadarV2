'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { X, Plus, Search } from 'lucide-react';

export interface FilterCriteria {
  id: string;
  field: string;
  operator: string;
  value: string | number | string[];
}

export interface AdvancedSearchCriteria {
  filters: FilterCriteria[];
  logic: 'AND' | 'OR';
  keyword: string;
  keywordFields: string[];
}

interface AdvancedSearchModalProps {
  open: boolean;
  onClose: () => void;
  onSearch: (criteria: AdvancedSearchCriteria) => void;
  initialCriteria?: AdvancedSearchCriteria;
}

const FIELD_OPTIONS = [
  { value: 'ticker', label: 'Ticker', type: 'text' },
  { value: 'company_name', label: 'Company Name', type: 'text' },
  { value: 'event_type', label: 'Event Type', type: 'select' },
  { value: 'title', label: 'Title', type: 'text' },
  { value: 'description', label: 'Description', type: 'text' },
  { value: 'direction', label: 'Direction', type: 'select' },
  { value: 'sector', label: 'Sector', type: 'select' },
  { value: 'info_tier', label: 'Info Tier', type: 'select' },
  { value: 'impact_score', label: 'Impact Score', type: 'number' },
  { value: 'confidence', label: 'Confidence', type: 'number' },
  { value: 'date', label: 'Date', type: 'date' },
];

const OPERATOR_OPTIONS = {
  text: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'contains', label: 'Contains' },
    { value: 'not_contains', label: 'Does Not Contain' },
  ],
  number: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'gt', label: 'Greater Than' },
    { value: 'gte', label: 'Greater Than or Equal' },
    { value: 'lt', label: 'Less Than' },
    { value: 'lte', label: 'Less Than or Equal' },
  ],
  select: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not Equals' },
    { value: 'in', label: 'In List' },
    { value: 'not_in', label: 'Not In List' },
  ],
  date: [
    { value: 'equals', label: 'On Date' },
    { value: 'gt', label: 'After' },
    { value: 'gte', label: 'On or After' },
    { value: 'lt', label: 'Before' },
    { value: 'lte', label: 'On or Before' },
  ],
};

const EVENT_TYPE_OPTIONS = [
  'sec_8k', 'sec_10q', 'fda_approval', 'fda_rejection', 'earnings',
  'ma_activity', 'product_launch', 'guidance_raise', 'guidance_lower'
];

const DIRECTION_OPTIONS = ['positive', 'negative', 'neutral', 'uncertain'];

const SECTOR_OPTIONS = ['technology', 'healthcare', 'biotech', 'finance', 'energy', 'consumer'];

const INFO_TIER_OPTIONS = ['primary', 'secondary'];

const KEYWORD_FIELD_OPTIONS = [
  { value: 'title', label: 'Title' },
  { value: 'description', label: 'Description' },
  { value: 'company_name', label: 'Company Name' },
  { value: 'ticker', label: 'Ticker' },
  { value: 'event_type', label: 'Event Type' },
  { value: 'sector', label: 'Sector' },
];

export function AdvancedSearchModal({
  open,
  onClose,
  onSearch,
  initialCriteria,
}: AdvancedSearchModalProps) {
  const [filters, setFilters] = useState<FilterCriteria[]>(
    initialCriteria?.filters || []
  );
  const [logic, setLogic] = useState<'AND' | 'OR'>(
    initialCriteria?.logic || 'AND'
  );
  const [keyword, setKeyword] = useState(initialCriteria?.keyword || '');
  const [keywordFields, setKeywordFields] = useState<string[]>(
    initialCriteria?.keywordFields || ['title', 'description', 'company_name']
  );

  const addFilter = () => {
    const newFilter: FilterCriteria = {
      id: Date.now().toString(),
      field: 'ticker',
      operator: 'equals',
      value: '',
    };
    setFilters([...filters, newFilter]);
  };

  const removeFilter = (id: string) => {
    setFilters(filters.filter((f) => f.id !== id));
  };

  const updateFilter = (id: string, updates: Partial<FilterCriteria>) => {
    setFilters(
      filters.map((f) => (f.id === id ? { ...f, ...updates } : f))
    );
  };

  const getFieldType = (field: string): string => {
    const fieldOption = FIELD_OPTIONS.find((opt) => opt.value === field);
    return fieldOption?.type || 'text';
  };

  const getOperatorsForField = (field: string) => {
    const fieldType = getFieldType(field);
    return OPERATOR_OPTIONS[fieldType as keyof typeof OPERATOR_OPTIONS] || OPERATOR_OPTIONS.text;
  };

  const toggleKeywordField = (field: string) => {
    if (keywordFields.includes(field)) {
      setKeywordFields(keywordFields.filter((f) => f !== field));
    } else {
      setKeywordFields([...keywordFields, field]);
    }
  };

  const handleSearch = () => {
    onSearch({
      filters,
      logic,
      keyword,
      keywordFields,
    });
  };

  const handleClear = () => {
    setFilters([]);
    setLogic('AND');
    setKeyword('');
    setKeywordFields(['title', 'description', 'company_name']);
  };

  const renderValueInput = (filter: FilterCriteria) => {
    const fieldType = getFieldType(filter.field);

    if (filter.operator === 'in' || filter.operator === 'not_in') {
      return (
        <input
          type="text"
          value={Array.isArray(filter.value) ? filter.value.join(', ') : filter.value}
          onChange={(e) => {
            const values = e.target.value.split(',').map((v) => v.trim());
            updateFilter(filter.id, { value: values });
          }}
          placeholder="Comma-separated values"
          className="flex-1 px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] placeholder-[--muted]"
        />
      );
    }

    if (fieldType === 'select') {
      let options: string[] = [];
      if (filter.field === 'event_type') options = EVENT_TYPE_OPTIONS;
      else if (filter.field === 'direction') options = DIRECTION_OPTIONS;
      else if (filter.field === 'sector') options = SECTOR_OPTIONS;
      else if (filter.field === 'info_tier') options = INFO_TIER_OPTIONS;

      return (
        <select
          value={filter.value as string}
          onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
          className="flex-1 px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
        >
          <option value="">Select...</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      );
    }

    if (fieldType === 'number') {
      return (
        <input
          type="number"
          value={filter.value}
          onChange={(e) => updateFilter(filter.id, { value: parseFloat(e.target.value) || 0 })}
          placeholder="Enter number"
          className="flex-1 px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] placeholder-[--muted]"
        />
      );
    }

    if (fieldType === 'date') {
      return (
        <input
          type="date"
          value={filter.value as string}
          onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
          className="flex-1 px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
        />
      );
    }

    return (
      <input
        type="text"
        value={filter.value}
        onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
        placeholder="Enter value"
        className="flex-1 px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] placeholder-[--muted]"
      />
    );
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Advanced Event Search</DialogTitle>
          <DialogDescription>
            Build complex search queries with multiple criteria, AND/OR logic, and keyword search.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[--text]">Filter Criteria</h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-[--muted]">Combine with:</span>
                <div className="flex gap-1 bg-[--surface-muted] rounded-lg p-1">
                  <button
                    onClick={() => setLogic('AND')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      logic === 'AND'
                        ? 'bg-[--primary] text-[--text-on-primary]'
                        : 'text-[--muted] hover:text-[--text]'
                    }`}
                  >
                    AND
                  </button>
                  <button
                    onClick={() => setLogic('OR')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      logic === 'OR'
                        ? 'bg-[--primary] text-[--text-on-primary]'
                        : 'text-[--muted] hover:text-[--text]'
                    }`}
                  >
                    OR
                  </button>
                </div>
              </div>
            </div>

            {filters.length === 0 ? (
              <div className="text-center py-8 bg-[--surface-muted] rounded-lg border border-dashed border-[--border]">
                <p className="text-[--muted] mb-3">No filters added yet</p>
                <Button onClick={addFilter} variant="outline" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add First Filter
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {filters.map((filter, index) => (
                  <div key={filter.id} className="flex items-center gap-2">
                    {index > 0 && (
                      <span className="text-xs font-semibold text-[--primary] w-12">
                        {logic}
                      </span>
                    )}
                    <select
                      value={filter.field}
                      onChange={(e) => {
                        const newField = e.target.value;
                        const newType = getFieldType(newField);
                        const newOperators = OPERATOR_OPTIONS[newType as keyof typeof OPERATOR_OPTIONS];
                        updateFilter(filter.id, {
                          field: newField,
                          operator: newOperators[0].value,
                          value: '',
                        });
                      }}
                      className="px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] w-48"
                    >
                      {FIELD_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>

                    <select
                      value={filter.operator}
                      onChange={(e) => updateFilter(filter.id, { operator: e.target.value })}
                      className="px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] w-48"
                    >
                      {getOperatorsForField(filter.field).map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>

                    {renderValueInput(filter)}

                    <button
                      onClick={() => removeFilter(filter.id)}
                      className="p-2 hover:bg-[--surface-hover] rounded-lg text-[--muted] hover:text-[--error] transition-colors"
                      title="Remove filter"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                ))}

                <Button onClick={addFilter} variant="outline" size="sm" className="w-full">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Filter
                </Button>
              </div>
            )}
          </div>

          <div className="border-t border-[--border] pt-6">
            <h3 className="text-sm font-semibold text-[--text] mb-3">Keyword Search</h3>
            <div className="space-y-3">
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="Enter keyword to search..."
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] placeholder-[--muted]"
              />

              <div>
                <p className="text-xs text-[--muted] mb-2">Search in fields:</p>
                <div className="flex flex-wrap gap-2">
                  {KEYWORD_FIELD_OPTIONS.map((field) => (
                    <label
                      key={field.value}
                      className="flex items-center gap-2 px-3 py-1.5 bg-[--surface-muted] hover:bg-[--surface-hover] rounded-lg cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={keywordFields.includes(field.value)}
                        onChange={() => toggleKeywordField(field.value)}
                        className="rounded border-[--border]"
                      />
                      <span className="text-sm text-[--text]">{field.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          <Button onClick={handleClear} variant="outline">
            Clear All
          </Button>
          <Button onClick={onClose} variant="outline">
            Cancel
          </Button>
          <Button onClick={handleSearch}>
            <Search className="h-4 w-4 mr-2" />
            Search
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
