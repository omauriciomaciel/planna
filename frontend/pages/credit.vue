<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const { format } = useCurrency()

interface CreditPurchase {
  id: string
  purchase_date: string
  credit_card_name: string | null
  merchant: string
  category_name: string | null
  total_amount: number
  installment_amount: number
  current_installment: number
  total_installments: number
  due_date: string | null
}

const purchases = ref<CreditPurchase[]>([])
const loading = ref(true)

async function loadPurchases() {
  loading.value = true
  try {
    purchases.value = await api.get<CreditPurchase[]>('/credit-purchases?limit=100')
  } finally {
    loading.value = false
  }
}

const columns: { accessorKey: keyof CreditPurchase | 'installment' | 'actions'; header: string }[] = [
  { accessorKey: 'purchase_date', header: 'Data' },
  { accessorKey: 'merchant', header: 'Estabelecimento' },
  { accessorKey: 'credit_card_name', header: 'Cartão' },
  { accessorKey: 'category_name', header: 'Categoria' },
  { accessorKey: 'installment', header: 'Parcela' },
  { accessorKey: 'installment_amount', header: 'Valor Parcela' },
  { accessorKey: 'total_amount', header: 'Valor Total' },
  { accessorKey: 'actions', header: '' },
]

async function deletePurchase(id: string) {
  await api.delete(`/credit-purchases/${id}`)
  await loadPurchases()
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

onMounted(loadPurchases)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">Compras no Crédito</h1>
    </div>

    <UCard>
      <UTable :data="purchases" :columns="columns" :loading="loading">
        <template #purchase_date-cell="{ row }">
          {{ formatDate(row.original.purchase_date) }}
        </template>
        <template #installment-cell="{ row }">
          {{ row.original.current_installment }}/{{ row.original.total_installments }}
        </template>
        <template #installment_amount-cell="{ row }">
          {{ format(row.original.installment_amount) }}
        </template>
        <template #total_amount-cell="{ row }">
          {{ format(row.original.total_amount) }}
        </template>
        <template #actions-cell="{ row }">
          <UButton
            variant="ghost"
            color="error"
            icon="i-heroicons-trash"
            size="xs"
            @click="deletePurchase(row.original.id)"
          />
        </template>
      </UTable>
    </UCard>
  </div>
</template>
