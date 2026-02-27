<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const { format } = useCurrency()

interface Transaction {
  id: string
  date: string
  due_date: string | null
  description: string
  account_name: string | null
  category_name: string | null
  type: string
  amount: number
  status: string
}

const transactions = ref<Transaction[]>([])
const loading = ref(true)

async function loadTransactions() {
  loading.value = true
  try {
    transactions.value = await api.get<Transaction[]>('/transactions?limit=100')
  } finally {
    loading.value = false
  }
}

const columns: { accessorKey: keyof Transaction | 'actions'; header: string }[] = [
  { accessorKey: 'date', header: 'Data' },
  { accessorKey: 'description', header: 'Descrição' },
  { accessorKey: 'account_name', header: 'Conta' },
  { accessorKey: 'category_name', header: 'Categoria' },
  { accessorKey: 'type', header: 'Tipo' },
  { accessorKey: 'amount', header: 'Valor' },
  { accessorKey: 'status', header: 'Status' },
  { accessorKey: 'actions', header: '' },
]

async function deleteTransaction(id: string) {
  await api.delete(`/transactions/${id}`)
  await loadTransactions()
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

onMounted(loadTransactions)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">Lançamentos</h1>
    </div>

    <UCard>
      <UTable :data="transactions" :columns="columns" :loading="loading">
        <template #date-cell="{ row }">
          {{ formatDate(row.original.date) }}
        </template>
        <template #type-cell="{ row }">
          <UBadge
            :color="row.original.type === 'income' ? 'success' : 'error'"
            variant="subtle"
          >
            {{ row.original.type === 'income' ? 'Entrada' : 'Saída' }}
          </UBadge>
        </template>
        <template #amount-cell="{ row }">
          <span :class="row.original.type === 'income' ? 'text-green-400' : 'text-red-400'">
            {{ format(row.original.amount) }}
          </span>
        </template>
        <template #status-cell="{ row }">
          <UBadge
            :color="row.original.status === 'paid' ? 'success' : 'warning'"
            variant="subtle"
          >
            {{ row.original.status === 'paid' ? 'Pago' : 'Não pago' }}
          </UBadge>
        </template>
        <template #actions-cell="{ row }">
          <UButton
            variant="ghost"
            color="error"
            icon="i-heroicons-trash"
            size="xs"
            @click="deleteTransaction(row.original.id)"
          />
        </template>
      </UTable>
    </UCard>
  </div>
</template>
